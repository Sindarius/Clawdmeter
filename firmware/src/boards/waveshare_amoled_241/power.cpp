#include "../../hal/power_hal.h"
#include "board.h"
#include <Arduino.h>

// No AXP2101 on this board. Power latch (BAT_CTRL_GPIO / GPIO16) is held
// HIGH by board_init() before this runs and must stay HIGH for battery
// operation. PWR button is BTN_PWR_GPIO (KEY_BAT / GPIO15), active LOW.
//
// Edge detection mirrors the AMOLED-1.8 IO expander approach:
//   short    — fired on release if the hold was shorter than PWR_LONG_MS
//   long     — fired once when a hold crosses PWR_LONG_MS
//   released — fired on every falling edge
//
// Battery voltage is available via ADC on BAT_ADC_GPIO (GPIO17), but the
// voltage divider ratio is not yet verified. battery_pct() returns -1
// (unknown) until calibrated — see TODO below.

#define PWR_POLL_MS  50
#define PWR_LONG_MS  1500

static bool     pwr_pressed_flag      = false;
static bool     pwr_long_flag         = false;
static bool     pwr_released_flag     = false;
static bool     last_pwr_state        = false;
static uint32_t pwr_press_started_ms  = 0;
static bool     pwr_long_fired        = false;
static uint32_t last_pwr_ms           = 0;

void power_hal_init(void) {
    // BTN_PWR_GPIO is active LOW with internal pull-up.
    pinMode(BTN_PWR_GPIO, INPUT_PULLUP);
    // BAT_CTRL_GPIO (power latch) is already HIGH from board_init().
}

void power_hal_tick(void) {
    uint32_t now = millis();
    if (now - last_pwr_ms < PWR_POLL_MS) return;
    last_pwr_ms = now;

    bool pwr_now = (digitalRead(BTN_PWR_GPIO) == LOW);   // active LOW
    if (pwr_now && !last_pwr_state) {                     // press begins
        pwr_press_started_ms = now;
        pwr_long_fired = false;
    } else if (pwr_now && last_pwr_state) {               // held
        if (!pwr_long_fired && (now - pwr_press_started_ms >= PWR_LONG_MS)) {
            pwr_long_flag  = true;
            pwr_long_fired = true;
        }
    } else if (!pwr_now && last_pwr_state) {              // release
        pwr_released_flag = true;
        if (!pwr_long_fired) pwr_pressed_flag = true;     // short press
    }
    last_pwr_state = pwr_now;
}

int power_hal_battery_pct(void) {
    // TODO: measure battery voltage via analogReadMilliVolts(BAT_ADC_GPIO),
    // apply the board's voltage divider ratio, map to 0..100.
    // Example (unverified — confirm divider from schematic):
    //   uint32_t mv = analogReadMilliVolts(BAT_ADC_GPIO) * 2;  // 1:1 divider?
    //   return constrain((int)(mv - 3000) * 100 / (4200 - 3000), 0, 100);
    return -1;
}

bool power_hal_is_charging(void) { return false; }
bool power_hal_is_vbus_in(void)  { return false; }

bool power_hal_pwr_pressed(void) {
    if (pwr_pressed_flag) { pwr_pressed_flag = false; return true; }
    return false;
}

bool power_hal_pwr_long_pressed(void) {
    if (pwr_long_flag) { pwr_long_flag = false; return true; }
    return false;
}

bool power_hal_pwr_released(void) {
    if (pwr_released_flag) { pwr_released_flag = false; return true; }
    return false;
}
