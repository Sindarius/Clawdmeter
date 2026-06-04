#include "board.h"
#include <Arduino.h>
#include <Wire.h>

// Called once at the very start of setup(), before any HAL device init.
// MUST set BAT_CTRL_GPIO HIGH first — on battery power, the MCU shuts down
// the moment the user releases the PWR button unless this latch is held.
extern "C" void board_init(void) {
    pinMode(BAT_CTRL_GPIO, OUTPUT);
    digitalWrite(BAT_CTRL_GPIO, HIGH);

    Wire.begin(IIC_SDA, IIC_SCL);

    // Hardware-reset the FT6336 touch controller before touch_hal_init() runs.
    pinMode(TP_RST, OUTPUT);
    digitalWrite(TP_RST, LOW);
    delay(10);
    digitalWrite(TP_RST, HIGH);
    delay(10);
}
