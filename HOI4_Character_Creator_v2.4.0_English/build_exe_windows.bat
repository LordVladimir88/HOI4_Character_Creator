@echo off
setlocal
title Build HOI4 Character Creator

cd /d "%~dp0"

echo.
echo [1/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt

echo.
echo [2/3] Cleaning previous build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] Creating the executable...
python -m PyInstaller --noconfirm --clean "HOI4_Character_Creator.spec"

echo.
if exist "dist\HOI4 Character Creator.exe" (
    echo Build completed.
    echo Executable:
    echo "%CD%\dist\HOI4 Character Creator.exe"
) else (
    echo The build failed.
)

echo.
pause
