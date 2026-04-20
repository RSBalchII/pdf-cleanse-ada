#!/bin/bash
# Build pdf-ada-processor for macOS (.dmg)
# Requires node18+ and pkg installed globally.

set -e  # Exit on error

echo "Installing dependencies..."
npm install --silent

echo "Building executables..."
npx pkg . \
    --targets node18-macos-x64 \
    --output pdf-ada-processor.dmg,pdf-ada-processor-universal.dmg

if [ $? -ne 0 ]; then
    echo "Packaging failed. Check that 'pkg' is installed and configured."
    exit 1
fi

# Verify outputs
if [ ! -f "pdf-ada-processor.dmg" ] && [ ! -f "pdf-ada-processor-universal.dmg" ]; then
    echo "ERROR: DMG files were not created."
    exit 1
fi

echo ""
echo "Build successful!"
echo "  • pdf-ada-processor.dmg (Intel Mac)"
echo "  • pdf-ada-processor-universal.dmg (Apple Silicon + Intel)"
echo ""
echo "Move the DMG to your target Mac and install by dragging the app to Applications."
