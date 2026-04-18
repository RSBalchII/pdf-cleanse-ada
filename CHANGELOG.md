# Changelog

All notable changes to the PDF ADA Compliance Processor.

## [Unreleased]

### Changed
- **Library Migration** — Migrated from `pikepdf` to `_pdf_utils` (using `pypdfium2`) for faster text extraction, image analysis, and robust metadata handling.
- **Compliance Checks** — Implemented missing Link Purpose check (`check_links`, WCAG 2.4.4) using utility layer; refactored Image counting (`count_images`) to use modern utilities.

### Fixed
- **Outdated Dependencies** — Replaced deprecated `pikepdf` usage across project with `_pdf_utils` wrapper, resolving issues with outdated parsing and lack of modern security features.
- `--auto` flag for `adobe_autotag_api.py` (non-interactive batch mode)
- `--auto` flag for `batch_auto_tag_acrobat.py` (non-interactive batch mode)
- `batch_auto_tag_acrobat.py` — Acrobat Pro COM batch processor

### Fixed
- Windows console emoji encoding in `adobe_autotag_api.py` and `batch_auto_tag_acrobat.py`
- Auth scope format: `openid AdobeID DCAPI` (space-separated, not comma-separated)
- Server simplified: removed OAuth proxy routes, direct credentials check
- UI auth badge simplified: shows credentials status (no OAuth dependency)

### Changed
- **Adobe Cloud API** — tested and verified working; 4/19 PDFs successfully auto-tagged
- **Cloud quota exhausted** after initial batch (free tier limit reached)
- **Acrobat Pro COM** — verified `TouchUp_AutoTag` cannot be triggered programmatically (Acrobat security restriction)
- Removed unused OAuth server files (`adobe_oauth_server.py`, `adobe_oauth_config.json`, `start_oauth.bat`, `batch_auto_tag.py`)
- Updated README.md with quota findings and Acrobat Pro Action Wizard recommendation

### Results (Session 2026-04-07)
- 4 PDFs successfully auto-tagged via Adobe Cloud API (with full structure tree)
- 9 PDFs already tagged (metadata fixed by pipeline)
- 6 PDFs need Acrobat Pro Auto-Tag (quota exhausted)
- All 19 PDFs delivered to `Downloads/ADA_Cleaned/`

## [0.1.0] — 2026-04-07

### Added
- Initial project commit
- Express web server with SSE terminal streaming
- Python/pikepdf metadata fixer (title, lang, MarkInfo, DisplayDocTitle)
- Deep compliance checker (WCAG/PDF-UA/Section 508)
- Web UI with drag-drop upload, progress bar, results table
- Pipeline: upload → fix → re-assess → sort → report
- Re-Assess endpoint for before/after comparison
- Adobe Acrobat COM automation (fallback)
- Raw binary PDF scanner for catalog detection
- `specs/` documentation directory with standards, diagrams, and planning
- `specs/standards/` — 7 numbered standards documenting pain points and fixes
- Playwright MCP browser automation configuration
- `.gitignore` for clean repository

### Fixed
- pdf-lib catalog access → switched to Python/pikepdf subprocess (Standard 001)
- pikepdf Array/Dict traversal crashes → `_is_array()`/`_is_dict()` helpers (Standard 002)
- Adobe COM automation unreliability → Adobe Cloud API as primary path (Standard 003)
- URL-encoded filename 404s → dual search with `decodeURIComponent` (Standard 004)
- Manual browser testing slowness → Playwright MCP (Standard 005)
- PDF language BOM markers → raw regex with BOM stripping (Standard 006)
- Pipeline sort logic → zero auto-fixable = compliant (Standard 007)
