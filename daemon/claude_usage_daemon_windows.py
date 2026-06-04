#!/usr/bin/env python3
"""Claude Usage Tracker Daemon — Windows (USB serial transport).

Reads the Claude OAuth token from the native-Windows credentials path,
polls the Anthropic API for rate-limit utilization data, and sends the
payload as a newline-terminated JSON line over USB serial (COM port).
"""

import asyncio
import datetime
import json
import logging
import logging.handlers
import os
import re
import signal
import sys
import threading
import time
from pathlib import Path

import httpx
import serial
import serial.tools.list_ports

PORT     = "COM3"       # default; override with CLAWDMETER_PORT env var
BAUDRATE = 115200
POLL_INTERVAL  = 60     # seconds between API polls
OPEN_RETRY     = 5      # seconds between port-open attempts
READ_TIMEOUT   = 0.1    # serial read timeout (non-blocking feel)

API_URL = "https://api.anthropic.com/v1/messages"
API_HEADERS_TEMPLATE = {
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "oauth-2025-04-20",
    "Content-Type": "application/json",
    "User-Agent": "claude-code/2.1.5",
}
API_BODY = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 1,
    "messages": [{"role": "user", "content": "hi"}],
}


def _build_file_logger() -> logging.Logger | None:
    """Create a rotating file logger for field diagnostics, or None.

    Autostart launches the tray under pythonw.exe, which has no console — stdout
    is discarded (and is in fact None, making print() unsafe). A rotating file is
    then the ONLY trail when the daemon stalls in the field. Windows-only: on the
    Linux dev box / CI the console print() suffices, and gating to win32 keeps the
    pure-helper unit tests from writing stray log files.
    """
    if sys.platform != "win32":
        return None
    logger = logging.getLogger("clawdmeter.daemon")
    if logger.handlers:
        return logger  # idempotent across re-import (tray imports this module)
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = base / "Clawdmeter" / "daemon.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=512 * 1024, backupCount=3, encoding="utf-8"
        )
    except OSError:
        return None  # best-effort — logging setup must never stop the daemon
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


_FILE_LOGGER = _build_file_logger()


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    try:
        print(line, flush=True)
    except (OSError, ValueError, AttributeError, RuntimeError):
        pass
    if _FILE_LOGGER is not None:
        _FILE_LOGGER.info(msg)


class AuthError(Exception):
    """Raised by poll_api on a genuine 401/403."""


async def poll_api(token: str) -> dict | None:
    headers = dict(API_HEADERS_TEMPLATE)
    headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.post(API_URL, headers=headers, json=API_BODY)
    except httpx.HTTPError as e:
        log(f"API call failed: {e}")
        return None
    if resp.status_code in (401, 403):
        log(f"API HTTP {resp.status_code}: {resp.text[:200]}")
        raise AuthError(resp.status_code)
    if resp.status_code >= 400:
        log(f"API HTTP {resp.status_code}: {resp.text[:200]}")
        return None

    def hdr(name: str, default: str = "0") -> str:
        return resp.headers.get(name, default)

    now = time.time()

    def reset_minutes(reset_ts: str) -> int:
        try:
            r = float(reset_ts)
        except ValueError:
            return 0
        mins = (r - now) / 60.0
        return int(round(mins)) if mins > 0 else 0

    def pct(util: str) -> int:
        try:
            return int(round(float(util) * 100))
        except ValueError:
            return 0

    payload = {
        "s":  pct(hdr("anthropic-ratelimit-unified-5h-utilization")),
        "sr": reset_minutes(hdr("anthropic-ratelimit-unified-5h-reset")),
        "w":  pct(hdr("anthropic-ratelimit-unified-7d-utilization")),
        "wr": reset_minutes(hdr("anthropic-ratelimit-unified-7d-reset")),
        "st": hdr("anthropic-ratelimit-unified-5h-status", "unknown"),
        "ok": True,
    }
    return payload


def _extract_access_token(blob: str) -> str | None:
    """Pull the accessToken out of a credentials blob."""
    blob = blob.strip()
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        tok = data.get("accessToken")
        if isinstance(tok, str) and tok.strip():
            return tok
        for v in data.values():
            if isinstance(v, dict):
                tok = v.get("accessToken")
                if isinstance(tok, str) and tok.strip():
                    return tok
    m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', blob)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_\-.~+/=]{20,}", blob):
        return blob
    return None


def _windows_credential_candidates() -> list[Path]:
    if override := os.environ.get("CLAUDE_CREDENTIALS_PATH"):
        return [Path(override)]
    if config_dir := os.environ.get("CLAUDE_CONFIG_DIR"):
        return [Path(config_dir) / ".credentials.json"]
    home = Path.home()
    local_appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    return [
        home / ".claude" / ".credentials.json",
        local_appdata / "Claude" / ".credentials.json",
        appdata / "Claude" / ".credentials.json",
    ]


def read_token() -> str | None:
    """Read the Claude OAuth access token from the first available credential file."""
    for path in _windows_credential_candidates():
        try:
            return _extract_access_token(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return None


def _read_expiry() -> str:
    for path in _windows_credential_candidates():
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            data = json.loads(raw)
            oauth = data.get("claudeAiOauth", {})
            expires_ms = oauth.get("expiresAt")
            if expires_ms is None:
                return "expiry unknown"
            dt = datetime.datetime.fromtimestamp(
                expires_ms / 1000, tz=datetime.timezone.utc
            )
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        except (TypeError, ValueError, OSError, AttributeError, json.JSONDecodeError):
            return "expiry unknown"
    return "expiry unknown"


def _effective_port() -> str:
    return os.environ.get("CLAWDMETER_PORT", PORT)


def _open_port() -> serial.Serial | None:
    """Try to open the serial port. Returns Serial on success, None on failure."""
    port = _effective_port()
    try:
        ser = serial.Serial(port, BAUDRATE, timeout=READ_TIMEOUT)
        log(f"Opened {port} at {BAUDRATE} baud")
        return ser
    except serial.SerialException as e:
        log(f"Cannot open {port}: {e}")
        return None


def _write_payload(ser: serial.Serial, payload: dict) -> bool:
    """Write a JSON line to the serial port. Returns True on success."""
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    try:
        ser.write(line.encode())
        ser.flush()
        log(f"Sent: {line.rstrip()}")
        return True
    except serial.SerialException as e:
        log(f"Write failed: {e}")
        return False


async def run_serial(stop_event: asyncio.Event, tray_state=None) -> None:
    """Main serial loop: open port → poll API on schedule → write JSON."""
    loop = asyncio.get_running_loop()
    last_poll = 0.0  # poll immediately on first connect

    while not stop_event.is_set():
        # --- open port ---
        ser = await loop.run_in_executor(None, _open_port)
        if ser is None:
            if tray_state:
                tray_state.set_scanning()
            log(f"Retrying in {OPEN_RETRY}s...")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=OPEN_RETRY)
            except asyncio.TimeoutError:
                pass
            continue

        if tray_state:
            tray_state.set_scanning()  # port open but no data sent yet

        # --- poll loop ---
        try:
            while not stop_event.is_set():
                # Drain any incoming serial lines (ack/nack from device)
                try:
                    while ser.in_waiting:
                        resp_line = ser.readline().decode(errors="replace").strip()
                        if resp_line:
                            log(f"Device: {resp_line}")
                except serial.SerialException as e:
                    log(f"Read error: {e}")
                    break

                now = time.time()
                if now - last_poll >= POLL_INTERVAL:
                    token = read_token()
                    if not token:
                        log("No token; skipping poll")
                        if tray_state:
                            tray_state.set_error("token expired — run claude login")
                    else:
                        try:
                            payload = await poll_api(token)
                        except AuthError:
                            if tray_state:
                                tray_state.set_error("token expired — run claude login")
                            payload = None

                        if payload is not None:
                            ok = await loop.run_in_executor(
                                None, _write_payload, ser, payload
                            )
                            if ok:
                                last_poll = time.time()
                                if tray_state:
                                    tray_state.set_connected(last_poll)
                            else:
                                break  # port lost — reopen

                await asyncio.sleep(1.0)

        except serial.SerialException as e:
            log(f"Serial error: {e}")
        finally:
            try:
                ser.close()
            except serial.SerialException:
                pass
            log("Port closed")
            if tray_state:
                tray_state.set_scanning()
            last_poll = 0.0  # poll immediately on reconnect


async def main(tray_state=None) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    if tray_state is not None:
        tray_state.loop = loop
        tray_state.stop_event = stop_event

    def _stop(*_args: object) -> None:
        log("Daemon stopping")
        stop_event.set()

    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _stop)
            except NotImplementedError:
                try:
                    signal.signal(sig, _stop)
                except ValueError:
                    pass

    log(f"=== Claude Usage Tracker Daemon (USB serial, Windows) ===")
    log(f"Port: {_effective_port()}  Poll interval: {POLL_INTERVAL}s")

    await run_serial(stop_event, tray_state)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
