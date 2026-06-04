#pragma once

// Waveshare ESP32-S3-Touch-AMOLED-2.41 — portrait AMOLED.
// RM690B0 AMOLED 450×600, FT6336 touch, QMI8658C IMU, 16 MB flash, 8 MB PSRAM.
// No AXP2101 PMU — power latch on BAT_CTRL_GPIO, PWR button (KEY_BAT) on
// BTN_PWR_GPIO, battery ADC on BAT_ADC_GPIO.
// LCD_RST and TP_RST are direct GPIOs (not via IO expander).
// TCA9554 IO expander is present on the PCB but not used by this firmware.

#define BOARD_NAME           "Waveshare AMOLED 2.41"

// ---- Display geometry (portrait) ----
#define LCD_WIDTH            450
#define LCD_HEIGHT           600

// ---- QSPI display pins (RM690B0) ----
#define LCD_CS               9
#define LCD_SCLK             10
#define LCD_SDIO0            11
#define LCD_SDIO1            12
#define LCD_SDIO2            13
#define LCD_SDIO3            14
// LCD reset is a direct GPIO on this board (unlike the AMOLED-1.8 which
// routes it through the XCA9554 IO expander).
#define LCD_RESET            21

// ---- I2C bus (shared by touch, IMU) ----
#define IIC_SDA              47
#define IIC_SCL              48

// ---- Touch (FT6336 — FocalTech family, same register layout as FT3168) ----
// No INT pin is connected to an MCU GPIO on this board; touch is polled
// every frame via I2C. TP_RST is a direct GPIO (strapping pin — safe to
// drive as output after boot is complete).
#define TP_RST               3
#define TP_ADDR              0x38

// ---- IMU (QMI8658C) ----
// Present and initialized for I2C bus health. Auto-rotation is disabled
// because the panel is mounted in a fixed portrait orientation.
#define QMI8658_ADDR         0x6B

// ---- Power management (no AXP2101) ----
// Hold BAT_CTRL_GPIO HIGH from the very first line of board_init() or the
// device will power off when the user releases the PWR button on battery.
#define BAT_CTRL_GPIO        16   // output HIGH = keep battery power latch on
#define BAT_ADC_GPIO         17   // ADC in — battery voltage divider (TODO: calibrate)
#define BTN_PWR_GPIO         15   // KEY_BAT — PWR button, active LOW with pull-up

// ---- Buttons ----
#define BTN_BACK_GPIO        0    // BOOT — primary, Space (PTT)

// ---- Capability flags ----
#define BOARD_HAS_SECONDARY_BUTTON 0
#define BOARD_HAS_ROTATION         0
#define BOARD_HAS_IMU              1   // QMI8658C present; rotation disabled (fixed portrait)
#define BOARD_HAS_BATTERY          0   // No AXP2101; ADC-based reading not yet calibrated
#define BOARD_HAS_IO_EXPANDER      0   // TCA9554 present on PCB but not driven by this firmware
