# Clawdmeter activity light — Claude Code hooks

The Clawdmeter stoplight (🟢 idle · 🟡 waiting on you · 🔴 working) is driven by
your **local Claude Code activity**, which the Anthropic usage API knows nothing
about. The daemon resolves that activity from two sources, in priority order:

1. **Hooks** (this folder) — precise and instant, and the only source that can
   tell "waiting on you" from "working". Reliable in the **terminal CLI**.
2. **Transcript watching** — automatic fallback, no setup. The daemon watches
   the newest `~/.claude/projects/**/*.jsonl` and infers busy-vs-idle from file
   activity. This is what covers the **desktop app's Code tab**, where
   `settings.json` hooks are currently unreliable. It can't detect the "waiting"
   state — that needs hooks.

So: **set up the hooks for the full three-color experience in the terminal.**
If you only ever use the desktop Code tab, you can skip them — the light still
works as a 🟢/🔴 busy indicator via transcript watching.

## How the hook works

`clawd_hook.py <state>` writes `"<state> <unix_ts>"` to `~/.claude/clawd-state`.
The daemon honors that file while it's fresh (30 s) and otherwise falls back to
the transcript watcher. Each hook is best-effort and always exits 0, so it can
never block or slow a session.

## Install

Add the block below to your **user** settings at `~/.claude/settings.json`
(merge it into any existing `"hooks"` object). Paths use the repo location
`D:\JR\Clawdmeter`; adjust if yours differs. JSON requires escaped backslashes.

If `python` isn't on your PATH, use an absolute interpreter path (e.g. the
daemon's venv: `D:\\JR\\Clawdmeter\\.venv\\Scripts\\python.exe`).

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "python \"D:\\JR\\Clawdmeter\\daemon\\hooks\\clawd_hook.py\" busy" } ] }
    ],
    "PreToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "python \"D:\\JR\\Clawdmeter\\daemon\\hooks\\clawd_hook.py\" busy" } ] }
    ],
    "PostToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "python \"D:\\JR\\Clawdmeter\\daemon\\hooks\\clawd_hook.py\" busy" } ] }
    ],
    "Notification": [
      { "hooks": [ { "type": "command", "command": "python \"D:\\JR\\Clawdmeter\\daemon\\hooks\\clawd_hook.py\" wait" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python \"D:\\JR\\Clawdmeter\\daemon\\hooks\\clawd_hook.py\" idle" } ] }
    ],
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "python \"D:\\JR\\Clawdmeter\\daemon\\hooks\\clawd_hook.py\" idle" } ] }
    ]
  }
}
```

### State mapping

| Hook event         | State written | Light |
|--------------------|---------------|-------|
| `UserPromptSubmit` | `busy`        | 🔴 you submitted; Claude is starting |
| `PreToolUse`       | `busy`        | 🔴 about to run a tool |
| `PostToolUse`      | `busy`        | 🔴 keeps the light fresh through long turns |
| `Notification`     | `wait`        | 🟡 Claude needs input / a permission approval |
| `Stop`             | `idle`        | 🟢 turn finished |
| `SessionStart`     | `idle`        | 🟢 session opened, nothing running yet |

> **Event names can vary by Claude Code version.** The set above is the common,
> stable core. If a `wait` or `idle` transition doesn't fire on your version,
> check `claude` → `/hooks` (or the hooks docs) for the current event names and
> adjust the keys; the `clawd_hook.py busy|wait|idle` commands stay the same.

## Verify

1. Start the daemon (`python daemon/claude_usage_daemon_windows.py`, or via the
   tray app) with the device plugged in.
2. In a **terminal** Claude Code session, submit a prompt → the device should go
   🔴. When Claude finishes → 🟢. Trigger a permission prompt → 🟡.
3. Check the signal directly: `type %USERPROFILE%\.claude\clawd-state` should
   show e.g. `busy 1718900000`.
