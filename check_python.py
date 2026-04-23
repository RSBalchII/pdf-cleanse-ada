#!/usr/bin/env python3
import sys
print("Python executable:", sys.executable)

# Check which pikepdf module is found
try:
    import pikepdf
    print("pikepdf version:", pikepdf.__version__)
    print("pikepdf location:", pikepdf.__file__)
except Exception as e:
    print("Error importing pikepdf:", e)

# Check sys.path
print("\nPython path entries:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")
