@echo off
REM PDF ADA Processor - Windows Launcher (PyInstaller)
REM Usage: pdf-ada.bat (double-click) or run from terminal

cd /d "%~dp0"
dist\pdf-ada.exe %*

pause
