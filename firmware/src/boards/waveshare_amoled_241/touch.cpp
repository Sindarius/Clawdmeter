#include "../../hal/touch_hal.h"
#include "board.h"
#include <Arduino.h>
#include <Wire.h>

// FT6336 capacitive touch controller (FocalTech family).
// Same register layout as FT3168 used on the AMOLED-1.8 board:
//   reg 0x02: low nibble = active finger count
//   reg 0x03/0x04: X1 high (low nibble) + X1 low
//   reg 0x05/0x06: Y1 high (low nibble) + Y1 low
//
// No INT pin is connected to a free MCU GPIO on this board, so touch state
// is polled on every call to touch_hal_read() rather than ISR-triggered.

static bool     touch_pressed = false;
static uint16_t touch_x       = 0;
static uint16_t touch_y       = 0;

static void touch_poll(void) {
    Wire.beginTransmission(TP_ADDR);
    Wire.write(0x02);
    if (Wire.endTransmission(false) != 0) { touch_pressed = false; return; }
    if (Wire.requestFrom(TP_ADDR, (uint8_t)5) != 5) { touch_pressed = false; return; }
    uint8_t fingers = Wire.read() & 0x0F;
    uint8_t xH      = Wire.read();
    uint8_t xL      = Wire.read();
    uint8_t yH      = Wire.read();
    uint8_t yL      = Wire.read();
    if (fingers == 0 || fingers > 5) {
        touch_pressed = false;
        return;
    }
    touch_x       = ((uint16_t)(xH & 0x0F) << 8) | xL;
    touch_y       = ((uint16_t)(yH & 0x0F) << 8) | yL;
    touch_pressed = true;
}

void touch_hal_init(void) {
    // Enable active scanning (FT6336 power-mode register 0xA5 = 0x00).
    Wire.beginTransmission(TP_ADDR);
    Wire.write(0xA5);
    Wire.write(0x00);
    Wire.endTransmission();

    // Read chip ID for boot diagnostics.
    Wire.beginTransmission(TP_ADDR);
    Wire.write(0xA0);
    if (Wire.endTransmission(false) == 0 && Wire.requestFrom(TP_ADDR, (uint8_t)1) == 1) {
        Serial.printf("FT6336 chip ID=0x%02X\n", Wire.read());
    } else {
        Serial.println("FT6336 ID read failed");
    }
}

void touch_hal_read(uint16_t* x, uint16_t* y, bool* pressed) {
    touch_poll();
    *x       = touch_x;
    *y       = touch_y;
    *pressed = touch_pressed;
}
