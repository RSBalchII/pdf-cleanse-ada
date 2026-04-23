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

# Check _pdf_utils location
import _pdf_utils
print("_pdf_utils location:", _pdf_utils.__file__)
