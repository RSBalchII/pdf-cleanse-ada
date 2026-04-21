@echo off
title Building PDF ADA Processor with PyInstaller...

cd /d "%~dp0"

echo Cleaning up old builds...
rmdir /s /q "dist" 2>nul
rmdir /s /q "build" 2>nul

echo Running PyInstaller...
pyinstaller pdf-ada.spec --clean --noconfirm

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build successful!
    echo Executable location: dist\pdf-ada.exe
) else (
    echo.
    echo Build failed with error code: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo Cleaning up temp files...
rmdir /s /q "build" 2>nul
del /f "pdf_ada.spec.pyc" 2>nul

pause
