#!/usr/bin/env python3
"""Claude Code hook → Clawdmeter activity state.

Wired into Claude Code's lifecycle hooks (see hooks-README.md), this writes the
current activity state to ``~/.claude/clawd-state`` where the daemon picks it up
and forwards it to the device as the stoplight color.

Usage (from a settings.json hook ``command``)::

    python /path/to/clawd_hook.py busy
    python /path/to/clawd_hook.py wait
    python /path/to/clawd_hook.py idle

The hook's stdin JSON (session info) is read and discarded — only the state
argument matters. Exits 0 unconditionally so a hook failure can never block
or slow down a Claude Code session.
"""

import sys
import time
from pathlib import Path

VALID = ("idle", "wait", "busy")
STATE_FILE = Path.home() / ".claude" / "clawd-state"


def main() -> int:
    state = sys.argv[1].lower() if len(sys.argv) > 1 else "idle"
    if state not in VALID:
        state = "idle"

    # Drain stdin (Claude Code pipes event JSON here) so the writer side never
    # blocks on a full pipe; we don't need its contents.
    try:
        sys.stdin.read()
    except Exception:
        pass

    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(f"{state} {time.time():.0f}\n", encoding="utf-8")
    except OSError:
        pass  # best-effort; never fail a hook

    return 0


if __name__ == "__main__":
    # Always exit 0 — a hook must not break the session.
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
