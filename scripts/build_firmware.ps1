# build_firmware.ps1 - Agnostic Firmware Build Runner
param (
    [switch]$Clean
)

$buildDir = "build"
# We define the SDK path relative to the script's location (the Bunker)
$sdkPath = "$PSScriptRoot/../lib/pico-sdk"

if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "`n[0/2] Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

if (!(Test-Path $buildDir)) {
    Write-Host "`n[1/2] Configuring CMake..." -ForegroundColor Cyan
    
    # CRITICAL FIX: We pass the PICO_SDK_PATH directly to CMake as a definition
    # This overrides any environment variable and ensures the bunker is found.
    cmake -S . -B $buildDir -G Ninja -DPICO_SDK_PATH="$sdkPath"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] CMake configuration failed." -ForegroundColor Red
        exit $LASTEXITCODE
    }
} else {
    Write-Host "`n[1/2] Build directory exists. Using incremental build..." -ForegroundColor Gray
}

Write-Host "[2/2] Compiling firmware with Ninja..." -ForegroundColor Green
Write-Host "------------------------------------------------------------"
cmake --build $buildDir

if ($LASTEXITCODE -eq 0) {
    Write-Host "------------------------------------------------------------"
    Write-Host "SUCCESS: Firmware is ready in /$buildDir" -ForegroundColor Green
    
    $uf2File = Get-ChildItem -Path $buildDir -Filter "*.uf2" -Recurse | Select-Object -First 1
    if ($uf2File) {
        Write-Host "Flashable file: $($uf2File.FullName)" -ForegroundColor Yellow
    }
} else {
    Write-Host "------------------------------------------------------------"
    Write-Host "ERROR: Compilation failed." -ForegroundColor Red
    exit $LASTEXITCODE
}