@echo off
setlocal

set PIO=%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\LocalCache\local-packages\Python310\Scripts\pio.exe
if not exist "%PIO%" set PIO=%USERPROFILE%\.platformio\penv\Scripts\pio.exe
set FIRMWARE=%~dp0firmware
set PORT=COM3

:: ── Board selection ──────────────────────────────────────────────────────────
echo.
echo  Clawdmeter firmware flash
echo  ─────────────────────────
echo  [1] waveshare_amoled_241      2.41"           (default)
echo  [2] waveshare_amoled_216      2.16" 480x480
echo  [3] waveshare_amoled_18       1.8"  368x448
echo  [4] waveshare_amoled_216_c6   2.16" C6 variant
echo.
set /p CHOICE="Board [1]: "

if "%CHOICE%"==""  set ENV=waveshare_amoled_241
if "%CHOICE%"=="1" set ENV=waveshare_amoled_241
if "%CHOICE%"=="2" set ENV=waveshare_amoled_216
if "%CHOICE%"=="3" set ENV=waveshare_amoled_18
if "%CHOICE%"=="4" set ENV=waveshare_amoled_216_c6

if not defined ENV (
    echo Unknown choice: %CHOICE%
    exit /b 1
)

:: ── Port selection ────────────────────────────────────────────────────────────
echo.
set /p PORTINPUT="Upload port [%PORT%]: "
if not "%PORTINPUT%"=="" set PORT=%PORTINPUT%

:: ── Flash ─────────────────────────────────────────────────────────────────────
echo.
echo  Building and flashing [%ENV%] to %PORT% ...
echo.

"%PIO%" run -d "%FIRMWARE%" -e %ENV% -t upload --upload-port %PORT%

if errorlevel 1 (
    echo.
    echo  Flash FAILED. Check the port and try again.
    exit /b 1
)

echo.
echo  Done.
endlocal
