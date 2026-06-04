#!/usr/bin/env python3
"""Unit tests for COM-port selection / switching — APP-01.

Covers:
  _effective_port() priority order (saved menu choice > env > default)
  get_saved_port / save_port round-trip and best-effort error handling
  list_serial_ports() shape and sort order
  run_serial honours TrayState.reconnect_flag (drops port, reopens new one)
  TrayState.request_reconnect() sets the flag

Run: python -m pytest daemon/tests/test_windows_port_select.py -x -q
"""
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import daemon.claude_usage_daemon_windows as mod
from daemon.tray_windows import TrayState


# ---------------------------------------------------------------------------
# _effective_port — priority order
# ---------------------------------------------------------------------------

def test_effective_port_default_when_nothing_set():
    """No saved choice and no env var → the PORT constant default."""
    with patch.object(mod, "get_saved_port", return_value=None), \
         patch.dict(mod.os.environ, {}, clear=False):
        mod.os.environ.pop("CLAWDMETER_PORT", None)
        assert mod._effective_port() == mod.PORT


def test_effective_port_env_overrides_default():
    """CLAWDMETER_PORT is used when no menu selection has been saved."""
    with patch.object(mod, "get_saved_port", return_value=None), \
         patch.dict(mod.os.environ, {"CLAWDMETER_PORT": "COM9"}, clear=False):
        assert mod._effective_port() == "COM9"


def test_effective_port_saved_beats_env_and_default():
    """An explicit menu selection always wins over env and default."""
    with patch.object(mod, "get_saved_port", return_value="COM4"), \
         patch.dict(mod.os.environ, {"CLAWDMETER_PORT": "COM9"}, clear=False):
        assert mod._effective_port() == "COM4"


# ---------------------------------------------------------------------------
# save_port / get_saved_port — persistence round-trip
# ---------------------------------------------------------------------------

def test_save_and_get_saved_port_roundtrip(tmp_path):
    """save_port writes the choice; get_saved_port reads it back (trimmed)."""
    cfg = tmp_path / "Clawdmeter" / "port.txt"
    with patch.object(mod, "_port_config_path", return_value=cfg):
        assert mod.save_port("COM4 ") is True
        assert cfg.read_text(encoding="utf-8") == "COM4"
        assert mod.get_saved_port() == "COM4"


def test_get_saved_port_none_when_absent(tmp_path):
    """A missing config file means 'no selection', not an error."""
    cfg = tmp_path / "Clawdmeter" / "port.txt"
    with patch.object(mod, "_port_config_path", return_value=cfg):
        assert mod.get_saved_port() is None


def test_get_saved_port_none_when_blank(tmp_path):
    """An empty/whitespace file is treated as no selection."""
    cfg = tmp_path / "Clawdmeter" / "port.txt"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("   \n", encoding="utf-8")
    with patch.object(mod, "_port_config_path", return_value=cfg):
        assert mod.get_saved_port() is None


def test_save_port_swallows_oserror():
    """save_port returns False (never raises) when the write fails."""
    with patch.object(mod, "_port_config_path",
                      return_value=Path("Z:/nonexistent/Clawdmeter/port.txt")), \
         patch("pathlib.Path.mkdir", side_effect=OSError("denied")):
        assert mod.save_port("COM4") is False


# ---------------------------------------------------------------------------
# list_serial_ports — enumeration shape
# ---------------------------------------------------------------------------

def test_list_serial_ports_shape_and_sort():
    """Returns (device, description) pairs sorted by device."""
    p3 = MagicMock(device="COM3", description="USB Serial Device")
    p4 = MagicMock(device="COM4", description="Silicon Labs CP210x")
    with patch.object(mod.serial.tools.list_ports, "comports",
                      return_value=[p4, p3]):
        result = mod.list_serial_ports()
    assert result == [
        ("COM3", "USB Serial Device"),
        ("COM4", "Silicon Labs CP210x"),
    ]


def test_list_serial_ports_falls_back_to_device_when_no_description():
    """A port with no description uses the device name as the description."""
    p = MagicMock(device="COM5", description=None)
    with patch.object(mod.serial.tools.list_ports, "comports", return_value=[p]):
        assert mod.list_serial_ports() == [("COM5", "COM5")]


def test_list_serial_ports_empty_on_enumeration_failure():
    """Enumeration errors yield an empty list, not an exception."""
    with patch.object(mod.serial.tools.list_ports, "comports",
                      side_effect=RuntimeError("driver gone")):
        assert mod.list_serial_ports() == []


# ---------------------------------------------------------------------------
# TrayState.request_reconnect
# ---------------------------------------------------------------------------

def test_request_reconnect_sets_flag():
    """request_reconnect flips reconnect_flag from its default False to True."""
    ts = TrayState()
    assert ts.reconnect_flag is False
    ts.request_reconnect()
    assert ts.reconnect_flag is True


# ---------------------------------------------------------------------------
# run_serial honours the reconnect flag (closes old port, reopens new one)
# ---------------------------------------------------------------------------

def test_run_serial_reopens_on_reconnect_flag():
    """Setting reconnect_flag while a port is open closes it and reopens.

    Drives run_serial with a fake serial port. On the first poll tick we set the
    reconnect flag; the loop must break, close the current port, and call
    _open_port again — proving a tray port-switch forces a reconnect.
    """
    ts = TrayState()

    opened = []

    def _fake_open():
        ser = MagicMock()
        ser.in_waiting = 0
        opened.append(ser)
        # Second open: stop the loop so the test terminates.
        if len(opened) >= 2:
            ts.stop_event.set()
        return ser

    # Trip the switch from INSIDE the poll loop (read_token runs after the port
    # is open and the open-time flag clear has happened), mirroring a real user
    # clicking a port while the daemon is already connected.
    def _trip_then_no_token():
        ts.reconnect_flag = True
        return None

    async def _drive():
        ts.stop_event = asyncio.Event()
        with patch.object(mod, "_open_port", side_effect=_fake_open), \
             patch.object(mod, "read_token", side_effect=_trip_then_no_token):
            await asyncio.wait_for(mod.run_serial(ts.stop_event, ts), timeout=5.0)

    asyncio.run(_drive())

    # Two opens => the port was dropped and reopened after the flag was set.
    assert len(opened) >= 2
    # The first port handle was closed when the loop dropped it.
    opened[0].close.assert_called()
    # The flag was consumed (cleared) by the reconnect path.
    assert ts.reconnect_flag is False
