# Setup Guide

Complete setup instructions for the PDF ADA Compliance Processor.

## Prerequisites

| Requirement | Version | Why |
|------------|---------|-----|
| **Node.js** | 18+ | Web server, file uploads, UI |
| **Python** | 3.10+ | PDF parsing, metadata fixes, compliance checking |
| **Git** (optional) | any | Version control |

### How to Check

```bash
node --version   # v18 or higher
python --version # Python 3.10 or higher  (use `python3` on Mac/Linux)
```

If either command fails, download and install:
- **Node.js:** https://nodejs.org/ (LTS recommended)
- **Python:** https://www.python.org/downloads/

---

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd pdf-cleanse-ada

# Node.js packages (express, multer, pdf-lib)
npm install

# Python packages in a virtual environment (avoids PEP 668 errors on macOS/Linux)
node setup.js
```

> **What `node setup.js` does:** Creates a `.venv` virtual environment, then installs `pikepdf`, `Pillow`, `requests`, and `pywin32` into it. No `externally-managed-environment` errors.

### 2. Start the Web UI

```bash
node server.js
```

The server auto-opens your browser at **http://localhost:3456**.

That's it — the app is ready to use.

---

## Detailed Setup

### Step 1: Clone or Download the Project

```bash
git clone https://github.com/RSBalchII/pdf-cleanse-ada.git
cd pdf-cleanse-ada
```

Or download the ZIP and extract.

### Step 2: Install Node.js Dependencies

```bash
npm install
```

This installs 3 packages defined in `package.json`:

| Package | Purpose |
|---------|---------|
| `express` | Web server framework |
| `multer` | File upload handling |
| `pdf-lib` | PDF metadata reading (title, page count) |

These are lightweight and install quickly (~30 seconds).

### Step 3: Install Python Dependencies (Virtual Environment)

```bash
node setup.js
```

This script:
1. **Creates a `.venv` virtual environment** — isolates Python packages from the system Python (required on macOS/Linux due to PEP 668)
2. **Installs 4 packages** from `requirements.txt` into `.venv`:

| Package | Purpose | Size | Notes |
|---------|---------|------|-------|
| **pikepdf** | PDF structure modification | ~50 MB | C++ bindings, pre-built wheels for Python 3.9-3.12 |
| **Pillow** | Image analysis | ~15 MB | For image/alt-text detection |
| **requests** | HTTP client | < 1 MB | Adobe API communication |
| **pywin32** | Windows COM access | ~10 MB | Windows only, optional (Acrobat automation) |

The server (`server.js`) and all subprocess calls automatically detect and use `.venv` when it exists.

**Why not just `pip install -r requirements.txt`?** On macOS and many Linux distributions, the system Python is "externally managed" (PEP 668) — `pip install` is blocked to prevent breaking OS tools. The virtual environment bypasses this cleanly.

**Do users need to manually install pikepdf?** No — `node setup.js` handles everything automatically.

### Step 4: Verify Installation

```bash
node -e "console.log('Node OK')"
python -c "import pikepdf; print('pikepdf OK')"
```

Both should print success messages. If pikepdf fails, your Python/pip setup may need attention.

### Step 5: Create Directories (Auto-created)

The app creates these folders on first run:

```
input_pdfs/          ← Drop PDFs here
done/                ← Compliant PDFs (auto-fixed)
needs_review/        ← PDFs needing Adobe auto-tag
adobe_tagged/        ← Adobe Cloud tagged PDFs
auto_fixed/          ← Acrobat Pro auto-tagged PDFs
assessment_results/  ← Compliance reports
pipeline_results/    ← CSV reports
fix_logs/            ← Fix operation logs
```

You can also create them manually, but the server does it automatically.

---

## Optional: Adobe Cloud Auto-Tag

For fully accessible PDFs with proper structure trees (headings, tables, lists, reading order), you need Adobe's auto-tag capability.

### Option A: Developer Credentials (Recommended)

1. Go to https://developer.adobe.com/console
2. Create a project
3. Add **PDF Services API**
4. Download credentials (client_id + client_secret)
5. Create `adobe_credentials.json`:

```json
{
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here"
}
```

6. Place the file in the project root

Free tier: 500 operations/month. After that, ~$0.05 per operation.

### Option B: No Credentials (Manual Acrobat Pro)

If you don't have developer credentials:

1. Click **🔧 Auto-Tag in Acrobat** in the UI
2. Acrobat Pro opens the PDF
3. In Acrobat: `Tools > Accessibility > Auto-Tag Document`
4. Save the file, then click **🔄 Re-Assess**

This method is **unlimited** (no quota) but requires manual steps.

---

## Troubleshooting

### Python not found

**Windows:**
```bash
py --version       # Try the Python launcher
python --version   # Try plain python
```

If neither works, install Python from https://www.python.org/downloads/ and check "Add Python to PATH" during install.

**Mac/Linux:**
```bash
python3 --version
```

### pip install fails on pikepdf

This happens on macOS/Linux because of PEP 668 (externally managed Python). Use the setup script instead:

```bash
node setup.js
```

This creates a `.venv` and installs everything there — no conflicts.

If `node setup.js` itself fails:
1. **Upgrade pip in venv:** `.venv/bin/pip install --upgrade pip` (macOS/Linux) or `.venv\Scripts\pip install --upgrade pip` (Windows)
2. **Check Python version:** Python 3.9-3.12 supported
3. **Try binary wheel:** `.venv/bin/pip install --only-binary :all: pikepdf`

If still failing, check https://pypi.org/project/pikepdf/#files for your platform.

### Node.js version too old

If `node --version` shows v16 or lower:

1. Download LTS from https://nodejs.org/
2. Or use nvm: `nvm install 18 && nvm use 18`

### Port 3456 already in use

The server runs on port 3456 by default. To change it, edit `server.js` line 24:
```javascript
const PORT = 3456;  // Change to any available port
```

### Acrobat Pro automation doesn't work

The `pywin32` package allows Acrobat COM automation on Windows, but Acrobat's `TouchUp_AutoTag` action **cannot be triggered programmatically** due to Acrobat security restrictions. The UI button opens PDFs in Acrobat for manual auto-tagging instead.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Chrome)                    │
│  http://localhost:3456                                  │
│  Upload PDFs → View results → Download fixed PDFs      │
└──────────────────────────┬──────────────────────────────┘
                           │
                    HTTP REST API
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   Node.js (server.js)                    │
│  ├─ Express server (port 3456)                          │
│  ├─ Multer (file uploads)                               │
│  ├─ pdf-lib (read PDF metadata)                         │
│  └─ Spawns Python processes for:                        │
│     ├─ pdf_fix_single.py (pikepdf metadata fix)         │
│     ├─ deep_scan.py (compliance checking)               │
│     ├─ compliance_checker.py (re-assess)                │
│     └─ adobe_autotag_api.py (Adobe Cloud API)           │
└──────────────────────────┬──────────────────────────────┘
                           │
                    subprocess (stdin/stdout)
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   Python (3.10+)                         │
│  ├─ pikepdf — PDF structure modification                │
│  ├─ Pillow — Image analysis                             │
│  ├─ requests — Adobe API HTTP calls                     │
│  └─ pywin32 — Windows COM (Acrobat)                     │
└─────────────────────────────────────────────────────────┘
```

**Why both Node.js and Python?**
- **Node.js** handles the web server, file uploads, and UI (fast, async, great ecosystem)
- **Python/pikepdf** handles PDF structure modification (pikepdf is the only open-source library that can modify PDF catalog objects like `/MarkInfo` and `/StructTreeRoot`)
- They communicate via **subprocess calls** with stdin/stdout/stderr

---

## Command Reference

| Command | Description |
|---------|-------------|
| `npm install && node setup.js` | Install all dependencies (creates .venv) |
| `node server.js` | Start web UI |
| `node setup.js` | Re-run Python setup / repair |
| `.venv/bin/python deep_scan.py input_pdfs/` | Run compliance scan from CLI (macOS/Linux) |
| `.venv\Scripts\python deep_scan.py input_pdfs/` | Run compliance scan from CLI (Windows) |
| `.venv/bin/python adobe_autotag_api.py --auto` | Non-interactive batch auto-tag (macOS/Linux) |

---

## System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 2 GB | 4 GB+ |
| Disk | 200 MB | 500 MB+ |
| CPU | Any modern | Multi-core (for parallel PDF processing) |

Processing speed: ~2-5 seconds per PDF for metadata fixes, 2-5 minutes per PDF for Adobe Cloud auto-tag.
