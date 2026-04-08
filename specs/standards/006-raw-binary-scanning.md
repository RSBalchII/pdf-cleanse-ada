# Standard 006: Raw Binary PDF Scanning for Catalog Detection

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** `pdf-tools.js`

## Pain Point

`pdf-lib` cannot expose many catalog-level entries needed for compliance detection:
- `/StructTreeRoot` — Is the PDF tagged?
- `/MarkInfo /Marked` — Is MarkInfo set?
- `/ParentTree` — Is reading order mapped?
- `/Lang` — What is the document language?
- `/Outlines` — Does the PDF have bookmarks?
- `/S /Figure`, `/S /Table`, `/S /TH` — What structure elements exist?

Without this information, the Node.js pipeline cannot accurately assess compliance before or after fixes.

## Root Cause

`pdf-lib` provides a high-level API that deliberately hides low-level PDF object details. It exposes title, page count, and basic metadata but not the full catalog dictionary.

## Fix Applied

Implemented a raw binary text scanner (`scanRawPdf`) that regex-matches the raw PDF byte buffer:

```javascript
function scanRawPdf(buffer) {
  const text = buffer.toString('binary');

  return {
    isTagged:        /\/StructTreeRoot/.test(text),
    hasParentTree:   /\/ParentTree/.test(text),
    isMarked:        /\/MarkInfo[\s\S]{0,200}\/Marked\s*\/?true/.test(text),
    imageCount:      (text.match(/\/Subtype\s*\/Image/g) || []).length,
    figureCount:     (text.match(/\/S\s*\/Figure/g) || []).length,
    hasBookmarks:    /\/Outlines/.test(text),
    thCount:         (text.match(/\/S\s*\/TH/g) || []).length,
    tableCount:      (text.match(/\/S\s*\/Table/g) || []).length,
    lang:            extractLang(text),
    figuresWithAlt:  countFiguresWithAlt(text),
  };
}
```

Language extraction handles multiple formats and BOM markers:

```javascript
function extractLang(text) {
  const match = text.match(/\/Lang\s*\(([^)]+)\)/) ||
                text.match(/\/Lang\s*\/([A-Za-z\-]+)/);
  if (!match) return null;
  let lang = match[1].replace(/[\x00-\x1f\x7f-\xff]/g, '').trim();
  // Strip UTF-16 BOM if present
  if (lang.startsWith('þÿ') || lang.startsWith('ÿþ')) {
    lang = lang.substring(2);
  }
  return lang;
}
```

## Definitive Standard

**Rule 1:** Raw binary scanning is the detection method for catalog entries that `pdf-lib` cannot expose.

**Rule 2:** The scanner reads the PDF as a binary string (`buffer.toString('binary')`) and uses regex patterns — it does NOT parse the PDF structure.

**Rule 3:** Language detection MUST handle:
- `/Lang (en-US)` — parenthesized string
- `/Lang /en-US` — name object
- UTF-16 BOM markers (`þÿ` or `ÿþ`) prefixing the language code

**Rule 4:** The scanner is read-only — it never modifies the PDF. All modifications go through the Python/pikepdf subprocess (Standard 001).

**Rule 5:** Figure alt-text detection uses a bounded regex pattern (`/S /Figure[\s\S]{0,500}/Alt\s*\(`) to find `/Alt` within 500 characters of `/Figure` — sufficient for most PDF structure but may miss deeply nested cases.

## Related Standards

- Standard 001 (pikepdf for modifications)
- Standard 002 (pikepdf for Python-side detection)

## References

- `pdf-tools.js` → `scanRawPdf()` function
- `pdf-tools.js` → `readPdfInfo()` — Combines pdf-lib + raw scan
