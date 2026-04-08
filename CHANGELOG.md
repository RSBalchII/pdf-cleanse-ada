# Changelog

All notable changes to the PDF ADA Compliance Processor.

## [Unreleased]

### Added
- Adobe Cloud API auto-tag integration (`adobe_autotag_api.py`)
- Web UI button ☁️ Adobe Cloud Auto-Tag
- Server endpoint `POST /api/adobe-autotag`
- Playwright MCP browser automation configuration
- `specs/` documentation directory with standards, diagrams, and planning
- `specs/standards/` — 7 numbered standards documenting pain points and fixes
- `specs/spec.md` — Architecture diagrams (ASCII art)
- `specs/tasks.md` — Task tracker
- `specs/plan.md` — Project plan and risk register
- `specs/doc_policy.md` — Documentation policy
- CHANGELOG.md
- `.gitignore` for clean repository

### Fixed
- pdf-lib catalog access → switched to Python/pikepdf subprocess (Standard 001)
- pikepdf Array/Dict traversal crashes → `_is_array()`/`_is_dict()` helpers (Standard 002)
- Adobe COM automation unreliability → Adobe Cloud API as primary path (Standard 003)
- URL-encoded filename 404s → dual search with `decodeURIComponent` (Standard 004)
- Manual browser testing slowness → Playwright MCP (Standard 005)
- PDF language BOM markers → raw regex with BOM stripping (Standard 006)
- Pipeline sort logic → zero auto-fixable = compliant (Standard 007)

### Changed
- README.md updated with full documentation and Adobe integration details
- Pain points section removed from README (moved to `specs/standards/`)
- `AUTO_TAGGED_DIR` added to pipeline directories

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
- 19 PDFs processed: 13 compliant, 6 need Adobe auto-tag
