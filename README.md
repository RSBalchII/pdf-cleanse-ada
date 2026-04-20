# PDF ADA Compliance Processor

Automated PDF accessibility remediation pipeline. Fixes metadata, runs Adobe Cloud auto-tag, and produces fully WCAG/PDF-UA/Section 508 compliant documents — with a web UI for guided manual fixes.

> **Note:** This project was migrated from `pdf-cleanse-ada`. Core utility logic (`_pdf_utils.py`) is currently being restored to enable full test execution. See [Pain Points](#pain-points-and-progress) for status.

```bash
cd pdf-cleanse-ada

# Install dependencies
npm install
pip install -r requirements.txt

# Start the web UI (requires port 3456)
node server.js
```

## Quick Overview

1. **Upload** PDFs via drag-drop or `input_pdfs/` folder.
2. **Process:** Fix metadata, run compliance checks (`check_links`, etc.).
3. **Auto-Tag (Optional):** Use Adobe Cloud API for structure tree tagging (see below).
4. **Verify:** Re-assess PDFs and sort into `done/` or `needs_review/`.

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

| Status | Issue | Notes |
|---------|--------|-------|
| ✅ Solved | Import crashes (`nul` file, wrong paths) | Fixed during migration. |
| ✅ Solved | Test infrastructure (`tests/`, `conftest.py`) | Skeleton set up; mock logic in place. |
| 🔄 In Progress | Core Utility Logic (`_pdf_utils.py`) | Required for actual PDF processing (not just testing). |
| ❌ Open | Actual Compliance Logic | Needs implementation of real checks vs. mocks. |

## Requirements
* **Node.js** 18+
* **Python** 3.10+
* **Adobe PDF Services API** credentials (optional)

```json
// npm packages: pdf-lib, express, multer
// Python packages: pikepdf>=9.0.0, Pillow>=10.0.0
```
