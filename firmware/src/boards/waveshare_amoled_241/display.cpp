#include "../../hal/display_hal.h"
#include "board.h"
#include <Arduino.h>
#include <Arduino_GFX_Library.h>

// RM690B0 AMOLED, 450×600 portrait, QSPI.
// The RM690B0 controller's maximum addressable area is 482×600. The panel's
// 450-wide image is centered in GRAM, so col_offset = (482 - 450) / 2 = 16.
// Verify visually — if the image is off-center, adjust RM690B0_COL_OFFSET.
// LCD_RESET (GPIO21) is driven directly by the GFX library during begin().

#define RM690B0_COL_OFFSET  16

static Arduino_DataBus* bus = nullptr;
static Arduino_RM690B0* gfx = nullptr;

void display_hal_init(void) {
    bus = new Arduino_ESP32QSPI(
        LCD_CS, LCD_SCLK, LCD_SDIO0, LCD_SDIO1, LCD_SDIO2, LCD_SDIO3);
    gfx = new Arduino_RM690B0(
        bus, LCD_RESET, 0 /* rotation */,
        LCD_WIDTH, LCD_HEIGHT,
        RM690B0_COL_OFFSET, 0 /* row_offset */, 0, 0);
}

void display_hal_begin(void) {
    gfx->begin();
    gfx->fillScreen(0x0000);
    gfx->setBrightness(200);
}

void display_hal_set_brightness(uint8_t level) {
    if (gfx) gfx->setBrightness(level);
}

void display_hal_fill_screen(uint16_t color) {
    if (gfx) gfx->fillScreen(color);
}

void display_hal_draw_bitmap(int32_t x, int32_t y, int32_t w, int32_t h,
                             const uint16_t* pixels) {
    if (gfx) gfx->draw16bitRGBBitmap(x, y, (uint16_t*)pixels, w, h);
}

void display_hal_tick(void) {
    // No rotation handling needed — this board is fixed portrait.
}

void display_hal_round_area(int32_t* x1, int32_t* y1, int32_t* x2, int32_t* y2) {
    // RM690B0 CASET/RASET registers require even-aligned boundaries.
    *x1 = *x1 & ~1;
    *y1 = *y1 & ~1;
    *x2 = *x2 | 1;
    *y2 = *y2 | 1;
}
