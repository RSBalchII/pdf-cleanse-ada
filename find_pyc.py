#!/usr/bin/env python3
import sys
import os
import _pdf_utils
print("Python executable:", sys.executable)
print("_pdf_utils location:", _pdf_utils.__file__)

# Check if pikepdf is available and where
try:
    import pikepdf
    print("pikepdf version:", pikepdf.__version__)
    print("pikepdf module:", pikepdf.__file__)
except Exception as e:
    print("Error importing pikepdf:", e)

# Check all Python interpreters
import subprocess
result = subprocess.run(['cmd', '/c', 'where.exe', 'python'], capture_output=True, text=True)
print("\n--- All python executables found by where.exe ---")
for line in result.stdout.split('\n'):
    if line.strip():
        print(line)
