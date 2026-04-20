# Changelog

All notable changes to `pdf-cleanse-ada` and its successor `pdf-ada`. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - Migration Session

### Changed
* **Repository Migration:** Moved from `pdf-cleanse-ada` to `pdf-ada` (new directory structure, clean slate for utility logic).
* **Dependency Cleanup:** Removed unused files (`adobe_oauth_server.py`, deprecated OAuth proxy routes).
* **Utility Logic Restoration:** Created `_pdf_utils.py` placeholder; tests currently running on mock logic.

### Fixed
* **Import Crashes:** Resolved `AssertionError: nul ... exists=True` and path-related crashes during migration.
* **Test Infrastructure:** Set up `tests/`, `conftest.py`. Tests run but return dummy data (missing core PDF processing).

### Added
* **Pain Point Documentation:** Updated README to reflect current state (Solved vs. In Progress).

## [0.1.0] - 2026-04-07

### Changed
* **Library Migration:** Switched from `pikepdf` to `_pdf_utils` (`pypdfium2`) for text extraction and metadata.
* **Compliance Checks:** Implemented missing Link Purpose check (`check_links`, WCAG 2.4.4).

### Fixed
* **Outdated Dependencies:** Replaced deprecated `pikepdf` usage with modern utilities across the project.
* **Auto-tag Flags:** Fixed Windows console encoding and auth scope formats in `adobe_autotag_api.py` and `batch_auto_tag_acrobat.py`.
* **Server Simplification:** Removed OAuth proxy routes; direct credentials check implemented.

### Added
* **Initial Project:** Web UI with SSE terminal, Python/pikepdf fixer, Adobe Acrobat COM automation, raw binary scanner.
* **Documentation:** `specs/standards/`, Playwright MCP config, `.gitignore`.
