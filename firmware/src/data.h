#pragma once
#include <Arduino.h>

// Live Claude Code activity state, driven by the host daemon's "cs" field.
// Resolved host-side from Claude Code hooks (precise) or a transcript-file
// watcher (fallback for the desktop Code tab where hooks may not fire).
enum ClaudeState {
    CLAUDE_UNKNOWN = 0,  // no session info yet — rendered as an unlit/grey lamp
    CLAUDE_IDLE,         // Claude finished its turn / waiting on you to start
    CLAUDE_WAITING,      // Claude needs your input or a permission approval
    CLAUDE_BUSY,         // Claude is actively thinking / running tools
};

struct UsageData {
    float session_pct;       // 5-hour window utilization (0-100)
    int session_reset_mins;  // minutes until session resets
    float weekly_pct;        // 7-day window utilization (0-100)
    int weekly_reset_mins;   // minutes until weekly resets
    char status[16];         // "allowed" or "limited"
    ClaudeState claude_state; // live activity state for the stoplight indicator
    bool ok;                 // data parse succeeded
    bool valid;              // false until first successful parse
};
