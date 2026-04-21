# PDF ADA Compliance Processor (PyInstaller)

Automated PDF accessibility remediation pipeline. Fixes metadata, runs Adobe Cloud auto-tag, and produces fully WCAG/PDF-UA/Section 508 compliant documents — with a web UI for guided manual fixes.

> **Note:** This project was migrated from `pdf-cleanse-ada`. Core utility logic (`_pdf_utils.py`) is currently being restored to enable full test execution. See [Pain Points](#pain-points-and-progress) for status.

## Quick Start (Development Mode)

### 1. Install Dependencies

```bash
cd pdf-ada

# Node.js packages (express, multer, pdf-lib)
npm install

# Python packages in a virtual environment (avoids PEP 668 errors on macOS/Linux)
node setup.js
```

### 2. Start the Web UI

```bash
# Uses PyInstaller bundle executable if available, or Node.js server directly
pdf-ada.bat        # Windows: runs from bundled executable
npm start          # Cross-platform: falls back to Node.js server (requires port 3456)
```

The server auto-opens your browser at **http://localhost:3456**.

---

## Quick Overview

1. **Upload** PDFs via drag-drop or `input_pdfs/` folder.
2. **Process:** Fix metadata, run compliance checks (`check_links`, etc.).
3. **Auto-Tag (Optional):** Use Adobe Cloud API for structure tree tagging (see below).
4. **Verify:** Re-assess PDFs and sort into `done/` or `needs_review/`.

## Build Process (PyInstaller) - **NEW**

### Overview: PyInstaller vs pkg Migration

The project migrated from Node.js `pkg` to **PyInstaller** for packaging the main processor executable. This change provides:
- **Cross-platform binaries**: Single `.exe` on Windows, `.dmg` on macOS
- **Simplified deployment**: No need to ship Node.js runtime; PyInstaller bundles everything
- **Faster startup**: Native Python execution vs Node.js process spawn overhead

| Feature | pkg (Old) | PyInstaller (Current) |
|---------|-----------|----------------------|
| Build Tool | `pkg` package manager | `pyinstaller pdf-ada.spec` |
| Output Format | `.exe` (Windows only) | `.exe`, `.dmg`, or universal bundle |
| Dependencies Bundled | Node.js runtime, npm modules | Python + all Python dependencies |
| Package Size | ~20 MB (includes Node.js) | ~45-76 MB (Python + pip deps) |
| Build Command | `pkg server.js --targets ...` | `pyinstaller pdf-ada.spec` |

### Building the PyInstaller Bundle

```bash
# Windows
build-pyinstaller.cmd        # Automated build script

# macOS/Linux
python -m pyinstaller pdf-ada.spec --clean
```

**Output:**
- **Windows**: `dist\pdf-ada.exe` (x64) or universal bundle
- **macOS**: `dist/\pdf-ada.app/Contents/MacOS/pdf-ada` + `.dmg` installer

### Running the Bundled Executable

#### Windows
```bash
# Run from dist folder directly
cd dist
.\pdf-ada.bat                # Wrapper script that handles args
pdf-ada.exe server           # Direct executable call (optional --dry-run flag)
```

#### macOS/Linux
```bash
cd dist
./pdf-ada                     # Universal bundle, uses system Python
./pdf-ada --server            # Start the web UI
--dry-run                     # Dry run mode (shows what would execute)
```

**Important:** When running from `dist/`, arguments are passed directly to the executable. For example:
```bash
# This will dispatch 'server' subcommand with any trailing args
python dist/pdf-ada.exe --server some-flag
```

---

## Pipeline Steps

```
Upload → Fix Metadata (Python/pikepdf) → Compliance Scan → Sort & Report
       (Title, Lang, MarkInfo)          (WCAG/PDF-UA checks)
```

### Step 1: Upload and Process
Drop PDFs into the UI or `input_pdfs/` folder, then click **▶ Process All PDFs**.

The pipeline reads each PDF, detects accessibility issues, applies auto-fixes, and sorts:

| Directory | Meaning |
|-----------|---------|
| `done/` | Fully compliant; all auto-fixable issues resolved. |
| `needs_review/` | Requires Adobe auto-tagging for structure tree or manual review. |

### Step 2: Adobe Cloud Auto-Tag ☁️ (Optional)
For PDFs in `needs_review/`, click **☁️ Adobe Cloud Auto-Tag**. This uses the official Adobe PDF Services API to:
1. Upload PDF to Adobe's cloud storage.
2. Run ML model for headings, tables, lists, reading order.
3. Download fully tagged PDF with `/StructTreeRoot`.

**Credentials Setup:**
```bash
# Option A: Create JSON file
{"client_id":"YOUR_ID","client_secret":"YOUR_SECRET"} > adobe_credentials.json
```
**Cost Note:** Free tier (~500 ops/month). Check [Pricing](https://developer.adobe.com/document-services/pricing/).

### Step 3: Re-Assess & Verify
After tagging, click **🔄 Re-Assess** to see before/after compliance comparison.

## Technical Details & Standards

| Section | Description |
|----------|-------------|
| [`specs/spec.md`](specs/spec.md) | Full architecture diagrams and flow. |
| [`specs/tasks.md`](specs/tasks.md) | Current task tracker (unresolved logic gaps). |
| [`specs/standards/`](specs/standards/) | Numbered standards documenting fixes and pain points. |

**Key Standards:**
* **001:** Migrated from `pdf-lib` to pikepdf for catalog safety.
* **002:** Implemented `_is_array()`/`_is_dict()` traversal helpers.
* **003-007:** See [`specs/standards`](specs/standards/) directory.

## Pain Points and Progress

| Status | Issue | Notes | Resolution |
|---------|--------|-------|------------|
| ✅ Solved | Import crashes (`nul` file, wrong paths) | Fixed during migration. | Updated `pdf-ada.spec` hidden imports |
| ✅ Solved | Test infrastructure (`tests/`, `conftest.py`) | Skeleton set up; mock logic in place. | PyInstaller bundles test dependencies |
| 🔄 In Progress | Core Utility Logic (`_pdf_utils.py`) | Required for actual PDF processing (not just testing). | Being restored to full utility functions |
| ❌ Open | Actual Compliance Logic | Needs implementation of real checks vs. mocks. | See `specs/tasks.md` |

## Known Issues with PyInstaller Implementation

### Issue 1: PATH Variable Interference with Extra Arguments

**Problem:** When running from `dist/`, arguments can be polluted by environment variables in PATH (e.g., `/path/to/server.js`).

**Resolution in `python/src/main.py`:**
```python
# Filter out full file paths that shouldn't be passed as subcommands
filtered_remaining = []
for arg in remaining:
    if isinstance(arg, str) and ('/' in arg or '\\' in arg):
        # It's a path, skip it (it came from PATH environment variable)
        continue
```

### Issue 2: Hardcoded Paths in Dispatch Function (Resolved)

**Problem:** The original dispatch function used a hardcoded absolute path (`C:\Users\rsbiiw\Projects\pdf-ada`) instead of resolving the project root dynamically. This broke portability when running from PyInstaller bundles on different systems.

**Resolution:** Changed to use dynamic path resolution based on `sys.executable`:
```python
# Get executable directory (where .exe/.app runs from)
exec_dir = Path(sys.executable).parent

# Project root is parent of python/src/
project_root = exec_dir.parent.parent / "python" / "..".resolve()
```

This ensures the project root is determined at runtime, regardless of where the executable was built.

### Issue 3: Argument Passing Between Layers

**Problem:** The dispatch function passes arguments through subprocess calls, but dry-run mode detection and filtering may lose information.

**Current Behavior:** Arguments are combined via `list(sub_args) + (list(remaining) if remaining else [])` and passed to `subprocess.run()`.

**Known Limitation:** Dry-run mode (`--dry-run`) is detected by checking for `'--dry-run' in arg`, but complex argument combinations may behave unexpectedly.

## Requirements
* **Node.js** 18+ (for development setup only)
* **Python** 3.10+ (required for PyInstaller bundle; used by `.exe` executable)
* **Adobe PDF Services API** credentials (optional, for auto-tagging)

### Development Dependencies
```json
// npm packages: express, multer, pdf-lib
// Python packages: pikepdf>=9.0.0, Pillow>=10.0.0
```

## File Structure After PyInstaller Migration

```
pdf-ada/
├── python/src/main.py              # Entry point for .exe executable (dispatch logic)
├── pdf-ada.spec                    # PyInstaller configuration file
├── build-pyinstaller.cmd           # Windows build automation script
├── adobe_credentials.json.template # Adobe API credentials template
├── package.json                    # Node.js deps (for dev only, not bundled by .exe)
└── dist/                           # Build output directory (contains pdf-ada.exe)
    └── pdf-ada.exe                # Final executable (bundles python + all deps)
```

When running the `.exe`, `python/src/main.py` is the entry point, which dispatches to one of these tools:
- `server` → runs Node.js web UI (`../server.js`)
- `ada-auto` → Adobe auto-tagging (`../adobe_auto.py`)
- `pdf-fix-single` → Single PDF metadata fix (`../pdf_fix_single.py`)
- and 5 other Python utilities

## Command Reference (from .exe)

| Command | Description | Example |
|---------|-------------|---------|
| `server` | Start web UI | `python dist/pdf-ada.exe server --dry-run` |
| `adobe-api` | Adobe Cloud auto-tag API | `python dist/pdf-ada.exe adobe-api --auto` |
| `pdf-fix-single` | Fix metadata on single PDF | `python dist/pdf-ada.exe pdf-fix-single input_pdfs/test.pdf` |
| `batch-tag-acrobat` | Batch tag with Acrobat COM | `python dist/pdf-ada.exe batch-tag-acrobat input/` |

## Architecture Overview (PyInstaller)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        PyInstaller Bundle Executable (.exe/.dmg)              │
│                                    ┌─────────┬──────────┬──────────┐       │
│                                    │ main.py │ server.js │ python  │       │
│                                    │ entry   │ (Node)    │ deps     │       │
│                                    └────┬────┼─────┬─────┴─────┬────┘       │
│                                        │   │  │      │          │           │
│                    ┌───────────────────▼──┼───▼───┼──────────────▼───────────┤
│                    │ Dispatch Logic (argp │ sub  │ subprocess calls          │
│                    │  + PATH filtering)   │ proc │ stdin/stdout              │
│                    └──────────────────────┴──────┘                           │
│                                        │                                      │
│                    ┌───────────────────▼─────────────────────────────────┐    │
│                    │ Python Dependencies Bundled by PyInstaller           │    │
│                    ├─ pikepdf (metadata fix)                             │    │
│                    ├─ Pillow (image analysis)                            │    │
│                    ├─ requests (Adobe API calls)                         │    │
│                    └─ pywin32 (Windows COM, optional)                    │    │
└──────────────────────────────────────────────────────────────────────────────┘

External Tools (not bundled):
  ├─ Node.js server.js (web UI, port 3456)                                │
  ├─ adobe_auto.py / batch_auto_tag_acrobat.py                            │
  └─ Other Python utilities in python/src/
```

**Why both PyInstaller and Node.js?**
- **PyInstaller bundle** handles standalone CLI execution (fast startup, no runtime required)
- **Node.js server** provides web UI for guided workflow (drag-drop uploads, real-time terminal output)
- They communicate via **subprocess calls** with stdin/stdout
