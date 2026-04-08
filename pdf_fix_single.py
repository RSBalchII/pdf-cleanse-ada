#!/usr/bin/env python3
"""Fix a single PDF's metadata. Reads from stdin, writes fixed PDF to stdout."""
import sys
import io
import json
import pikepdf
from pikepdf import Name, Dictionary

def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_fix_single.py <stem_name>", file=sys.stderr)
        sys.exit(1)

    stem = sys.argv[1]
    data = sys.stdin.buffer.read()
    fixes = []

    with pikepdf.open(io.BytesIO(data)) as pdf:
        # Fix Title
        if not pdf.Root.get("/Title"):
            pdf.Root.Title = stem
            fixes.append(f"Set title to '{stem}'")

        # Fix Language
        if not pdf.Root.get("/Lang"):
            pdf.Root.Lang = "en-US"
            fixes.append("Set /Lang to 'en-US'")

        # Fix MarkInfo
        mark_info = pdf.Root.get("/MarkInfo")
        if not mark_info:
            pdf.Root.MarkInfo = Dictionary()
            mark_info = pdf.Root.MarkInfo
        if mark_info.get("/Marked") is not True:
            mark_info.Marked = True
            fixes.append("Set MarkInfo.Marked = true")

        # Fix ViewerPreferences.DisplayDocTitle
        vp = pdf.Root.get("/ViewerPreferences")
        if not vp:
            pdf.Root.ViewerPreferences = Dictionary()
            vp = pdf.Root.ViewerPreferences
        if vp.get("/DisplayDocTitle") is not True:
            vp.DisplayDocTitle = True
            fixes.append("Set DisplayDocTitle = true")

        # Write fixed PDF to stdout
        out = io.BytesIO()
        pdf.save(out)
        sys.stdout.buffer.write(out.getvalue())

    # Write fixes to stderr as JSON
    print(json.dumps(fixes), file=sys.stderr)

if __name__ == "__main__":
    main()
