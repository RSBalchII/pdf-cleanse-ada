@echo off
REM Check which Python interpreters are available and their versions

echo Checking Python interpreters...
echo.

"C:\Users\rsbiiw\pdf-ada\.venv\Scripts" >nul 2>&1 && python.exe -c "import sys; print('pdf-ada venv:', sys.executable)" 
".venv\Scripts\python.exe" -c "import sys; print('temp venv:', sys.executable)"

echo.
echo Checking pikepdf installation...
"C:\Users\rsbiiw\pdf-ada\.venv\Scripts" >nul 2>&1 && python.exe -m pip show pikepdf | findstr /i "name version location" 
".venv\Scripts\python.exe" -m pip show pikepdf | findstr /i "name version location"

echo.
echo Checking _pdf_utils location...
"C:\Users\rsbiiw\pdf-ada\.venv\Scripts" >nul 2>&1 && python.exe -c "import _pdf_utils; print('pdf-ada venv:', _pdf_utils.__file__)" 
".venv\Scripts\python.exe" -c "import _pdf_utils; print('temp venv:', _pdf_utils.__file__)"

pause
