$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/3] Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt

Write-Host "[2/3] Cleaning..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }

Write-Host "[3/3] Building..."
python -m PyInstaller --noconfirm --clean "HOI4_Character_Creator.spec"

$exe = Join-Path $PSScriptRoot "dist\HOI4 Character Creator.exe"

if (Test-Path $exe) {
    Write-Host ""
    Write-Host "Build completed:"
    Write-Host $exe
} else {
    throw "The executable was not created."
}
