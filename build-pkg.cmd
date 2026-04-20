@echo off
rem Build pdf-ada-processor for Windows (.exe and .dng)
rem Requires node18+ and pkg installed globally.

echo Installing dependencies...
npm install --silent

echo Building executables...
npx pkg . --targets node18-win-x64 --output pdf-ada-processor.exe,pdf-ada-processor.dng

if errorlevel 1 (
  echo Packaging failed.  Check that "pkg" is installed and configured.
  exit /b 1
)

rem Verify outputs
if not exist "pdf-ada-processor.exe" (
  echo ERROR: pdf-ada-processor.exe was not created.
  exit /b 1
)

if not exist "pdf-ada-processor.dng" (
  echo ERROR: pdf-ada-processor.dng was not created.
  exit /b 1
)

echo Build successful: pdf-ada-processor.exe and pdf-ada-processor.dng created.