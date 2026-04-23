@echo off
REM Check which Python interpreters are available from both folders

echo Checking pdf-ada venv...
"C:\Users\rsbiiw\Projects\pdf-ada\.venv\Scripts" >nul 2>&1 & python.exe -c "import sys; print('pdf-ada venv:', sys.executable)" 

echo.
echo Checking temp venv...
".venv\Scripts\python.exe" -c "import sys; print('temp venv:', sys.executable)"

pause
