#!/usr/bin/env python3
"""Unit tests for the Claude Code activity-state resolver (clawd_state).

Covers the two-source priority logic: a fresh hook-written state file wins;
otherwise the newest transcript's mtime decides busy-vs-idle.

Run: python -m pytest daemon/tests/test_clawd_state.py -x -q
"""
import os

from daemon.clawd_state import (
    BUSY_WINDOW_S,
    HOOK_FRESH_S,
    resolve_state,
)

NOW = 1_700_000_000.0  # fixed clock so tests never depend on wall time


def _hook(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def _transcript(projects_dir, rel, mtime):
    """Create a transcript jsonl at projects_dir/rel and stamp its mtime."""
    p = projects_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"type":"assistant"}\n', encoding="utf-8")
    os.utime(p, (mtime, mtime))
    return p


# ---------------------------------------------------------------------------
# No sources
# ---------------------------------------------------------------------------

def test_no_sources_defaults_to_idle(tmp_path):
    state_file = tmp_path / "clawd-state"      # does not exist
    projects = tmp_path / "projects"
    projects.mkdir()
    assert resolve_state(NOW, state_file, projects) == "idle"


# ---------------------------------------------------------------------------
# Hook file
# ---------------------------------------------------------------------------

def test_fresh_hook_busy(tmp_path):
    sf = _hook(tmp_path / "clawd-state", f"busy {NOW:.0f}")
    assert resolve_state(NOW, sf, tmp_path / "projects") == "busy"


def test_fresh_hook_wait(tmp_path):
    sf = _hook(tmp_path / "clawd-state", f"wait {NOW:.0f}")
    assert resolve_state(NOW, sf, tmp_path / "projects") == "wait"


def test_fresh_hook_idle(tmp_path):
    sf = _hook(tmp_path / "clawd-state", f"idle {NOW:.0f}")
    assert resolve_state(NOW, sf, tmp_path / "projects") == "idle"


def test_stale_hook_ignored_falls_back(tmp_path):
    """A hook older than the freshness window is dropped; with no transcript we
    fall back to idle (not the stale 'busy')."""
    stale = NOW - HOOK_FRESH_S - 10
    sf = _hook(tmp_path / "clawd-state", f"busy {stale:.0f}")
    projects = tmp_path / "projects"
    projects.mkdir()
    assert resolve_state(NOW, sf, projects) == "idle"


def test_invalid_hook_word_ignored(tmp_path):
    sf = _hook(tmp_path / "clawd-state", f"garbage {NOW:.0f}")
    projects = tmp_path / "projects"
    projects.mkdir()
    assert resolve_state(NOW, sf, projects) == "idle"


def test_empty_hook_file_ignored(tmp_path):
    sf = _hook(tmp_path / "clawd-state", "")
    projects = tmp_path / "projects"
    projects.mkdir()
    assert resolve_state(NOW, sf, projects) == "idle"


def test_hook_without_timestamp_uses_mtime(tmp_path):
    """No embedded ts → trust the file mtime. A just-written file is fresh."""
    sf = tmp_path / "clawd-state"
    sf.write_text("busy", encoding="utf-8")
    os.utime(sf, (NOW, NOW))
    assert resolve_state(NOW, sf, tmp_path / "projects") == "busy"


# ---------------------------------------------------------------------------
# Transcript fallback
# ---------------------------------------------------------------------------

def test_transcript_recent_is_busy(tmp_path):
    projects = tmp_path / "projects"
    _transcript(projects, "proj-a/session.jsonl", NOW - 1)  # within busy window
    assert resolve_state(NOW, tmp_path / "clawd-state", projects) == "busy"


def test_transcript_old_is_idle(tmp_path):
    projects = tmp_path / "projects"
    _transcript(projects, "proj-a/session.jsonl", NOW - BUSY_WINDOW_S - 30)
    assert resolve_state(NOW, tmp_path / "clawd-state", projects) == "idle"


def test_newest_transcript_wins(tmp_path):
    """Busy is decided by the most-recently-touched transcript across projects."""
    projects = tmp_path / "projects"
    _transcript(projects, "proj-a/old.jsonl", NOW - 600)
    _transcript(projects, "proj-b/nested/new.jsonl", NOW - 1)  # recent
    assert resolve_state(NOW, tmp_path / "clawd-state", projects) == "busy"


# ---------------------------------------------------------------------------
# Priority: a fresh hook overrides the transcript
# ---------------------------------------------------------------------------

def test_fresh_hook_overrides_busy_transcript(tmp_path):
    sf = _hook(tmp_path / "clawd-state", f"idle {NOW:.0f}")
    projects = tmp_path / "projects"
    _transcript(projects, "proj-a/session.jsonl", NOW - 1)  # would say busy
    assert resolve_state(NOW, sf, projects) == "idle"
