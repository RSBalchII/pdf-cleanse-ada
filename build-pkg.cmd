@echo off
rem Build a single‑file Node executable for pdf‑ada‑processor
rem Requires node18+ and pkg installed globally.

:: Install npm dependencies if missing
npm install --silent

:: Run pkg to bundle the project into an .exe (win only)
npx pkg . --targets node18-win-x64 --output pdf-ada-processor.exe

if errorlevel 1 (
 echo Packaging failed.  Check that "pkg" is installed.
) else (
 echo Build complete: pdf-ada‑processor.exe created.
)