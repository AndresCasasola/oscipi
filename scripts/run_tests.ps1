# run_tests.ps1 - Native Unit Test Runner
$buildDir = "build_tests"
$testExec = "$buildDir/run_tests.exe"

# 1. Create build directory if it doesn't exist
if (!(Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

Write-Host "`n[1/3] Cleaning up old binaries..." -ForegroundColor Gray
if (Test-Path $testExec) { Remove-Item $testExec }

Write-Host "[2/3] Compiling test environment..." -ForegroundColor Cyan
gcc -DUNIT_TEST `
    -Ilib/unity/src `
    -Isrc `
    test/test_main.c `
    src/main.c `
    lib/unity/src/unity.c `
    -o $testExec

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Test compilation failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[3/3] Executing Unity..." -ForegroundColor Green
Write-Host "------------------------------------------------------------"
if (Test-Path $testExec) {
    & $testExec
}
Write-Host "------------------------------------------------------------"