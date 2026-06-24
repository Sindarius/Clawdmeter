#!/usr/bin/env python3
"""Resolve the live Claude Code *activity* state for the stoplight indicator.

The Anthropic usage API only reports quota consumption — it has no idea whether
Claude is thinking right now. So the green/yellow/red light comes from a second
signal, resolved here from two sources in priority order:

  1. Hook state file  (``~/.claude/clawd-state``) — written by Claude Code hooks
     (see ``daemon/hooks/clawd_hook.py``). Format: ``"<state> <unix_ts>"`` e.g.
     ``"busy 1718900000"``. Precise and low-latency, and the *only* source that
     can distinguish "waiting on you" from "working". Honored while fresh.
     Reliable in the terminal CLI.

  2. Transcript watcher — newest ``*.jsonl`` under ``~/.claude/projects/**``.
     A recent append means Claude is actively writing the turn (busy); a quiet
     file means idle. This needs zero per-machine setup and works on the desktop
     Code tab, where ``settings.json`` hooks are unreliable. It can only tell
     busy from idle — the "waiting" state needs hooks.

Returned states are the short codes the firmware parses: ``"idle"``, ``"wait"``,
``"busy"``.
"""

from __future__ import annotations

import time
from pathlib import Path

# Source locations. Overridable as args (used by tests).
_CLAUDE_DIR = Path.home() / ".claude"
STATE_FILE = _CLAUDE_DIR / "clawd-state"
PROJECTS_DIR = _CLAUDE_DIR / "projects"

# A hook-written state is trusted only this long. Keeps a crashed/orphaned
# "busy" from sticking forever, and lets the transcript watcher take over once
# the hook signal goes stale.
HOOK_FRESH_S = 30.0

# A transcript appended-to within this window is treated as an active turn.
BUSY_WINDOW_S = 5.0

_VALID = ("idle", "wait", "busy")


def _read_hook_state(now: float, state_file: Path) -> str | None:
    """Return a fresh hook-written state, or None if missing/stale/invalid."""
    try:
        raw = state_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None

    parts = raw.split()
    word = parts[0].lower()
    if word not in _VALID:
        return None

    ts: float | None = None
    if len(parts) >= 2:
        try:
            ts = float(parts[1])
        except ValueError:
            ts = None
    if ts is None:
        # No embedded timestamp — fall back to the file's own mtime.
        try:
            ts = state_file.stat().st_mtime
        except OSError:
            return None

    if now - ts > HOOK_FRESH_S:
        return None
    return word


def _newest_transcript_mtime(projects_dir: Path) -> float:
    """mtime of the most-recently-touched session transcript, or 0.0 if none."""
    newest = 0.0
    try:
        candidates = projects_dir.glob("**/*.jsonl")
    except OSError:
        return 0.0
    for p in candidates:
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if m > newest:
            newest = m
    return newest


def resolve_state(
    now: float | None = None,
    state_file: Path | None = None,
    projects_dir: Path | None = None,
) -> str:
    """Resolve the current activity state: one of "idle", "wait", "busy"."""
    if now is None:
        now = time.time()
    state_file = state_file or STATE_FILE
    projects_dir = projects_dir or PROJECTS_DIR

    hook = _read_hook_state(now, state_file)
    if hook is not None:
        return hook

    mtime = _newest_transcript_mtime(projects_dir)
    if mtime <= 0.0:
        return "idle"
    return "busy" if (now - mtime) <= BUSY_WINDOW_S else "idle"
