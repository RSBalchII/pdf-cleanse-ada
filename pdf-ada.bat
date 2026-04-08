@echo off
REM PDF ADA Processor - Windows Launcher
REM Usage: pdf-ada.bat [command] [options]

cd /d "%~dp0"
node pdf-processor.js %*
