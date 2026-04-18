# flash_pico.ps1 - Automates flashing the Raspberry Pi Pico using picotool

$uf2_path = "build/oscipi.uf2"

# 1. Check if the firmware exists
if (!(Test-Path $uf2_path)) {
    Write-Host "[ERROR] Firmware not found at '$uf2_path'." -ForegroundColor Red
    Write-Host "Please build the project first using './scripts/build_firmware.ps1'." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] Forcing Raspberry Pi Pico into BOOTSEL mode..." -ForegroundColor Cyan
# -f: Force
# -u: Reboot to BOOTSEL mode
picotool reboot -f -u

if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] picotool could not force reboot." -ForegroundColor Yellow
    Write-Host "The Pico might already be in BOOTSEL mode, or it's not connected." -ForegroundColor Yellow
} else {
    Write-Host "Success! Waiting for USB enumeration..." -ForegroundColor Green
    Start-Sleep -Seconds 2
}

Write-Host "`n[2/3] Flashing firmware to Pico..." -ForegroundColor Cyan
# -x: Execute after flashing
picotool load -x $uf2_path

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Flashing failed. Make sure picotool is installed and in your PATH." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[3/3] Done! The Pico is now running the new firmware." -ForegroundColor Green
