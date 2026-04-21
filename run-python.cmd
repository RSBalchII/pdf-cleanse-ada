@echo off
title PDF ADA Processor - Python Console
REM Usage: run-python.cmd (double-click) or run from terminal

cd /d "%~dp0"
python python\src\main.py %*

pause
