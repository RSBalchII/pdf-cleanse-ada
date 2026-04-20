@echo off
REM PDF ADA Processor - Windows Launcher
REM Usage: pdf-ada.bat (double-click) or run from terminal

cd /d "%~dp0"
node pdf-processor.js %*
