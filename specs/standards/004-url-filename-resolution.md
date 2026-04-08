# Standard 004: URL-Encoded Filename Resolution

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** `server.js`

## Pain Point

PDF filenames with spaces and special characters (e.g., `"NMT 2025 CITI Training Guide.pdf"`) are URL-encoded by the browser (`%20` for spaces). When these encoded names are sent to server endpoints, direct `path.join(dir, fileName)` lookups fail with 404 errors because the filesystem has the original filename, not the URL-encoded version.

This affected:
- `/api/auto-tag` — Open PDF in Acrobat
- `/api/re-assess` — Re-check compliance
- `/api/results/:type/:name` — Download result PDFs

## Root Cause

Browser `fetch()` and `XMLHttpRequest` automatically URL-encode filenames in request bodies and paths. The server receives encoded strings that don't match filesystem entries.

## Fix Applied

Server endpoints search across all possible directories with both raw and decoded versions:

```javascript
const searchDirs = [INPUT_DIR, DONE_DIR, NEEDS_REVIEW_DIR, ADOBE_FIXED_DIR, AUTO_TAGGED_DIR];
let pdfPath = null;

for (const dir of searchDirs) {
  // Try raw filename first
  const candidate = path.join(dir, fileName);
  if (existsSync(candidate)) {
    pdfPath = candidate;
    break;
  }
  // Try URL-decoded version
  try {
    const decoded = decodeURIComponent(fileName);
    if (decoded !== fileName) {
      const candidate2 = path.join(dir, decoded);
      if (existsSync(candidate2)) {
        pdfPath = candidate2;
        break;
      }
    }
  } catch {}
}
```

## Definitive Standard

**Rule 1:** ALL server endpoints that resolve a filename to a filesystem path MUST search across all output directories: `INPUT_DIR`, `DONE_DIR`, `NEEDS_REVIEW_DIR`, `AUTO_TAGGED_DIR`, `AUTO_FIXED_DIR`, `ADOBE_FIXED_DIR`.

**Rule 2:** For each directory, the endpoint MUST try both:
- The raw filename as received
- `decodeURIComponent(filename)` if it differs from the raw version

**Rule 3:** The search MUST stop at the first match (priority order of directories matters — earlier dirs take precedence).

**Rule 4:** All `path.join()` calls MUST use `path.join()` — never string concatenation — for cross-platform compatibility.

## Related Standards

- Standard 003 (Adobe Cloud API file handling)

## References

- `server.js` → `/api/auto-tag` and `/api/re-assess` endpoints
- `pdf-tools.js` → `AUTO_TAGGED_DIR` constant
