#pragma once
#include <lvgl.h>

// Design tokens — single source of truth for UI colors. Anthropic-inspired
// dark palette, AMOLED-friendly (true black bg).
#define THEME_BG       lv_color_hex(0x000000)   // screen background
#define THEME_PANEL    lv_color_hex(0x1f1f1e)   // card/zone fill
#define THEME_TEXT     lv_color_hex(0xfaf9f5)   // primary text
#define THEME_DIM      lv_color_hex(0xb0aea5)   // secondary text
#define THEME_ACCENT   lv_color_hex(0xd97757)   // brand terra-cotta
#define THEME_GREEN    lv_color_hex(0x788c5d)
#define THEME_AMBER    lv_color_hex(0xd97757)
#define THEME_RED      lv_color_hex(0xc0392b)
#define THEME_BAR_BG   lv_color_hex(0x2a2a28)   // unfilled bar track

// Stoplight / activity-state tokens. THEME_AMBER above is actually the
// terra-cotta accent, so the "waiting" lamp needs its own distinct gold to
// read as a true yellow between the red and green lamps.
#define THEME_STATUS_IDLE  THEME_GREEN              // idle / ready
#define THEME_STATUS_WAIT  lv_color_hex(0xd9a441)   // waiting on you (gold)
#define THEME_STATUS_BUSY  THEME_RED                // actively working
#define THEME_STATUS_OFF   lv_color_hex(0x3a3a36)   // unlit lamp / unknown
