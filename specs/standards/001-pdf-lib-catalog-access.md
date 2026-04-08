# Standard 001: PDF Library Selection for Catalog-Level Modifications

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** `pdf_fix_single.py`, `pdf-tools.js`

## Pain Point

`pdf-lib` (Node.js) can set `/Title` via `PDFDocument.setTitle()` but **cannot reliably write** the following catalog-level entries required for PDF/UA compliance:

- `/MarkInfo` — Must contain `/Marked true`
- `/ViewerPreferences` — Must contain `/DisplayDocTitle true`
- `/StructTreeRoot` — The tagged structure tree root
- `/ParentTree` — Content-to-structure mapping for reading order

Attempting to set these via `pdf-lib` either silently fails, corrupts the PDF, or writes entries that Adobe Acrobat's accessibility checker does not recognize.

## Root Cause

`pdf-lib` is designed for high-level PDF manipulation (pages, annotations, forms, metadata) and intentionally abstracts away the low-level PDF object model. It does not expose direct dictionary manipulation at the `/Catalog` level where accessibility flags live.

## Fix Applied

Delegated **all catalog-level modifications** to Python/pikepdf via a stdin/stdout subprocess pipe:

```
┌─────────────┐   stdin (PDF bytes)   ┌──────────────┐
│  Node.js    │ ─────────────────────►│  Python      │
│  (pdf-lib)  │                        │  (pikepdf)   │
│             │ ◄───────────────────── │              │
└─────────────┘   stdout (PDF bytes)   └──────────────┘
                      stderr (JSON fixes)
```

Implementation in `pdf-tools.js`:
```javascript
const proc = spawn(pythonCmd, [scriptPath, stem], { stdio: ['pipe', 'pipe', 'pipe'] });
proc.stdin.write(pdfBuffer);
proc.stdin.end();
// stdout → fixed PDF, stderr → JSON array of fixes applied
```

## Definitive Standard

**Rule 1:** All PDF catalog-level modifications (`/MarkInfo`, `/ViewerPreferences`, `/StructTreeRoot`, `/ParentTree`) MUST be performed via Python/pikepdf subprocess.

**Rule 2:** `pdf-lib` in Node.js is restricted to:
- Reading document title (`getTitle()`)
- Counting pages (`getPageCount()`)
- Loading and saving PDFs (for piping to Python)

**Rule 3:** The subprocess contract is:
- **stdin:** Raw PDF bytes
- **stdout:** Fixed PDF bytes (or original on error)
- **stderr:** Single JSON array of fix descriptions (e.g., `["Set title to 'X'", "Set /Lang to 'en-US'"]`)

**Rule 4:** If Python/pikepdf is unavailable, the pipeline degrades gracefully by returning the original PDF with no fixes applied.

## Related Standards

- Standard 003 (Adobe COM vs Cloud API)
- Standard 006 (Raw binary scanning for detection)

## References

- `pdf_fix_single.py` — The Python fix script implementing this standard
- `pdf-tools.js` → `fixPdf()` — The Node.js subprocess wrapper
- [pikepdf documentation](https://pikepdf.readthedocs.io/)
