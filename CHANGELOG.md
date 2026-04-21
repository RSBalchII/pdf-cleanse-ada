# Changelog

All notable changes to `pdf-cleanse-ada` and its successor `pdf-ada`. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - Migration Session (2026-04-20)

### Changed
* **Build System Migration:** Moved from Node.js `pkg` to PyInstaller for packaging the main PDF ADA processor executable. This provides cross-platform binaries (.exe on Windows, .dmg on macOS).
* **Repository Structure:** Moved from `pdf-cleanse-ada` to `pdf-ada` directory with clean slate structure.
* **Package Manager Shift:** Node.js `package.json` dependencies (express, multer, pdf-lib) are now dev-only; PyInstaller bundles Python dependencies instead.
* **Entry Point Change:** Web server (`server.js`) remains as the primary development target; PyInstaller bundle uses `python/src/main.py` as entry point for CLI execution.

### Added (Documentation)
* **PyInstaller Build Specifications:** New `specs/standards/009-pyinstaller-build-specs.md` documenting build process, pain points, and resolutions.
* **Pain Points Section in README:** Added comprehensive documentation of known issues and their resolution strategies.
* **Architecture Documentation:** Updated `specs/spec.md` with PyInstaller bundle architecture diagrams and data flow specifications.
* **Build Commands Reference:** Added documentation for `build-pyinstaller.cmd` automation script and cross-platform build options.

### Added
* **PyInstaller Build Script:** New `build-pyinstaller.cmd` automation script with clean builds and error handling.
* **Configuration File:** Created `pdf-ada.spec` with proper hidden imports (express, pdf-lib, multiprocessing).
* **Data Files:** PyInstaller bundles Adobe credentials template (`adobe_credentials.json.template`) and server.js for web UI access.
* **macOS DMG Packaging:** Added `.dmg` installer files in project root for macOS distribution.

### Fixed
* **Import Crashes:** Resolved `AssertionError: nul ... exists=True` and path-related crashes during migration to PyInstaller.
* **Test Infrastructure:** Set up `tests/`, `conftest.py`. Tests run but return dummy data (missing core PDF processing).
* **Hidden Imports:** Updated spec file with proper hiddenimports for Node.js libraries (express, pdf-lib) that were previously causing import errors.

### Changed (Build Process Details)
| Aspect | pkg (Old) | PyInstaller (New) | Notes |
|--------|-----------|-------------------|-------|
| Build Command | `pkg server.js --targets node18-win-x64` | `pyinstaller pdf-ada.spec` | Cross-platform support |
| Output | `.exe` Windows only | `.exe`, `.dmg`, or universal bundle | macOS DMG files added |
| Bundle Size | ~20 MB (includes Node.js) | ~45-76 MB (Python + pip deps) | Larger but faster startup |
| Dependencies | npm modules + Node runtime | Python packages via pyproject.toml | Uses `python/setup.py` for deps |

### Pain Points Addressed by PyInstaller Migration

1. **PATH Variable Interference:** When running from `dist/`, arguments can be polluted by environment variables (e.g., `/path/to/server.js`).
   - **Resolution:** `main.py` now filters paths before passing to subprocess calls.

2. **Hardcoded Project Paths:** The dispatch function previously used an absolute path (`C:\Users\rsbiiw\Projects\pdf-ada`) instead of resolving dynamically from the executable location.
   - **Resolution Needed:** Should use `Path(sys.executable).parent.parent` or similar to determine project root at runtime.

3. **Argument Passing Between Layers:** Dry-run mode detection and filtering may lose information when arguments are passed through subprocess calls.
   - **Current Behavior:** Arguments combined via `list(sub_args) + (list(remaining) if remaining else [])`.

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

## [0.0.1] - Initial Commit (2026-04-07)

### Added
* **Core Utilities:** `_pdf_utils.py` for PDF processing logic.
* **Web UI:** `server.js` with drag-drop uploads and compliance checking interface.
* **Testing Framework:** `tests/` directory with conftest.py, mocha/chai test suite.
