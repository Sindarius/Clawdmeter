#include "../../hal/imu_hal.h"
#include "board.h"
#include <Arduino.h>
#include <Wire.h>
#include <SensorQMI8658.hpp>

// QMI8658C is present and initialized for I2C bus health, but auto-rotation
// is disabled — the panel is in a fixed portrait orientation in the enclosure.

static SensorQMI8658 imu;

void imu_hal_init(void) {
    if (!imu.begin(Wire, QMI8658_ADDR, IIC_SDA, IIC_SCL)) {
        Serial.println("QMI8658 init failed");
        return;
    }
    Serial.println("QMI8658 init OK (rotation disabled on this board)");
}

void    imu_hal_tick(void)             {}   // no-op — rotation disabled
uint8_t imu_hal_rotation_quadrant(void) { return 0; }
