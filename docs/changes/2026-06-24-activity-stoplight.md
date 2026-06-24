# Claude activity stoplight (idle / waiting / busy)

**Date:** 2026-06-24
**Branch:** `feat/tray-com-port-switch`

Adds a green/yellow/red indicator that tracks what the local Claude Code session
is doing — 🟢 idle, 🟡 waiting on you (input/permission), 🔴 busy (thinking/
running tools) — shown both as a corner dot on the usage screen and as a
dedicated full-screen stoplight.

## Why it needed a new signal

The Anthropic usage API the daemon already polls only reports quota
consumption; it has no idea whether Claude is thinking right now. So activity
state is resolved from a **second source**, host-side, and rides the existing
USB-serial JSON line as one new field (`"cs"`).

Two sources, in priority order (`daemon/clawd_state.py`):

1. **Claude Code hooks** — precise, instant, and the only source that can
   distinguish "waiting on you" from "busy". Reliable in the **terminal CLI**.
2. **Transcript watcher** — newest `~/.claude/projects/**/*.jsonl` mtime; recent
   append ⇒ busy, quiet ⇒ idle. Zero setup, and the fallback that covers the
   **desktop app's Code tab**, where `settings.json` hooks are currently
   unreliable. Can only tell busy from idle — "waiting" needs hooks.

A fresh hook state (≤30 s old) wins; otherwise the transcript decides.

## Changes

### Firmware
- `data.h` — `ClaudeState` enum (`UNKNOWN/IDLE/WAITING/BUSY`) + field on `UsageData`.
- `theme.h` — `THEME_STATUS_IDLE/WAIT/BUSY/OFF`. New gold (`#d9a441`) for the
  "waiting" lamp, since the existing `THEME_AMBER` is actually the terra-cotta
  accent and wouldn't read as a true yellow.
- `main.cpp` — `parse_json` now returns a `parse_kind_t`; it only overwrites
  usage figures on a full payload, so a state-only `{"cs":...}` line updates the
  light without clobbering cached usage or polluting the rate-sampler.
- `ui.{h,cpp}` — `SCREEN_STATUS`; corner stoplight dot on the usage screen; a
  dedicated vertical 3-lamp stoplight screen with a status word; `ui_set_claude_state()`
  lights the active lamp (full color + glow) and dims the rest. A single forward
  tap cycle reaches everything: USAGE → STATUS → SPLASH → USAGE.

### Daemon
- `clawd_state.py` (new) — `resolve_state()`; paths injectable for tests.
- `claude_usage_daemon_windows.py` — caches the last usage payload; every 1 s
  tick resolves state and emits `"cs"` on change or on a usage refresh, so the
  light updates within ~1 s without extra API polls.
- `hooks/clawd_hook.py` (new) — writes `~/.claude/clawd-state`; always exits 0.
- `hooks/hooks-README.md` (new) — ready-to-paste `settings.json` block + state map.

### Tests
- `tests/test_clawd_state.py` — 12 cases (hook freshness/priority, transcript
  mtime busy/idle, nested glob, invalid/empty hook). All pass.

## Wire protocol

The daemon's JSON line gains an optional `"cs"` field: `"idle" | "wait" | "busy"`.
State-only lines omit the usage keys; the firmware leaves cached usage untouched.

## Not done in this environment / follow-ups
- **No compile build or on-device screenshot** — PlatformIO (`pio`) isn't
  installed here. Build with `pio run -d firmware -e waveshare_amoled_241` and
  screenshot-verify the status screen + dot before merging.
- Hook **event names vary by Claude Code version** — the README block is the
  stable core; verify `Notification`/`Stop` fire on the installed version.
- 4 pre-existing daemon tests fail on `scan_for_device` (stale BLE-era tests),
  unrelated to this change (confirmed by re-running against the unmodified file).
