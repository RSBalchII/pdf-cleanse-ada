# PDF ADA Compliance Processor

Automated PDF accessibility remediation pipeline. Fixes metadata, runs Adobe Cloud auto-tag, and produces fully WCAG/PDF-UA/Section 508 compliant documents — with a web UI for guided manual fixes.

```
  Upload → Fix Metadata → Adobe Cloud Auto-Tag → Re-Assess → Sort & Report
          (Python/pikepdf)   (Adobe PDF Services API)  (deep scan)
```

## Quick Start

```bash
cd pdf-cleanse-ada

# Install dependencies
npm install
pip install -r requirements.txt

# Start the web UI
node server.js
# → opens http://localhost:3456 in your browser
```

## Pipeline Overview

```
┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐
│  Upload PDF │ → │ Fix Metadata     │ → │ Adobe Cloud      │ → │ Re-Assess &  │
│  (drag-drop)│   │ (Python/pikepdf) │   │ Auto-Tag (API)   │   │ Sort Results │
└─────────────┘   └──────────────────┘   └──────────────────┘   └──────────────┘
```

### Step 1: Upload & Process

Drop PDFs into the UI or `input_pdfs/` folder, then click **▶ Process All PDFs**.

The pipeline reads each PDF, detects accessibility issues, applies auto-fixes, and sorts:

| Outcome | Directory | What Happened |
|---------|-----------|---------------|
| ✓ Compliant | `done/` | All auto-fixable issues resolved |
| ⚠ Needs Review | `needs_review/` | Requires Adobe auto-tag for structure tree |

### Step 2: Adobe Cloud Auto-Tag ☁️

For PDFs in `needs_review/`, click **☁️ Adobe Cloud Auto-Tag**. This uses the **official Adobe PDF Services API** to:

1. **Upload** PDF to Adobe's cloud storage (presigned URL)
2. **Auto-Tag** — Adobe's ML model identifies headings, tables, lists, figures, reading order
3. **Download** fully tagged PDF with complete structure tree

```
  needs_review/  →  Adobe API (2-5 min/PDF)  →  adobe_tagged/
```

**Credentials setup** (first time):

```bash
# Option A: Create adobe_credentials.json
echo '{"client_id":"...","client_secret":"..."}' > adobe_credentials.json

# Option B: Environment variables
export ADOBE_CLIENT_ID="your-client-id"
export ADOBE_CLIENT_SECRET="your-client-secret"

# Option C: First click of ☁️ button prompts interactively
```

Get credentials at: https://developer.adobe.com/console → Create Project → Add PDF Services API

### Step 3: Re-Assess & Verify

After Adobe tagging, click **🔄 Re-Assess** next to any PDF to run the compliance checker again and see before/after comparison inline.

### Step 4: Deep Scan (Optional)

Click **🔍 Deep Scan (Python)** to run the full compliance checker against all PDFs with structured results grouped by fixability.

## Adobe Integration

### Why Adobe Cloud API?

PDF tagging requires mapping content streams (text, images, tables) to a structure tree (`/StructTreeRoot`). This involves:
- Detecting visual hierarchy → heading levels
- Identifying table cells → `/TH`, `/TD`, `/TR` structure
- Finding list items → `/L`, `/LI`, `/Lbl`, `/LBody`
- Determining reading order → `/ParentTree`
- Extracting image semantics → `/Figure` with `/Alt` text

**No open-source library does this reliably.** The structure tree is a semantic representation, not just a PDF object. Adobe's auto-tag ML model is the industry standard.

### How the Integration Works

```
pdf-cleanse-ada                              Adobe PDF Services API
┌──────────────────┐                         ┌────────────────────┐
│                  │   1. POST /ims/token    │                    │
│  adobe_autotag.py├────────────────────────►│  Adobe IMS Auth    │
│                  │   2. 200 {access_token} │                    │
└────────┬─────────┘                         └────────────────────┘
         │
         │   3. POST /assets
         │      {mediaType: "application/pdf"}
         │   4. 200 {assetID, uploadUri}
         ▼
┌─────────────────┐                         ────────────────────┐
│                  │   5. PUT uploadUri      │                    │
│  adobe_autotag.py├────────────────────────►│  S3 Storage        │
│                  │   6. 200 OK             │                    │
└────────┬─────────┘                         └────────────────────┘
         │
         │   7. POST /operation/autotag
         │      {assetID, shiftHeadings, generateReport}
         │   8. 201 Location: /operation/autotag/{jobID}/status
         ▼
┌────────┴─────────┐                         ┌────────────────────┐
│                  │   9. GET .../{jobID}/   │  Auto-Tag Engine   │
│  Poll loop       ├────────────────────────►│  (ML model)        │
│  every 15s       │   10. {status: "done"}  │                    │
└─────────────────┘                         └────────────────────┘
         │
         │   11. GET /assets/{assetID}
         │   12. 200 {downloadUri}
         ▼
┌────────┴─────────┐                         ┌────────────────────┐
│                  │   13. GET downloadUri   │                    │
│  Save tagged PDF ├────────────────────────►│  S3 Storage        │
│  → adobe_tagged/ │   14. 200 (PDF bytes)   │                    │
└──────────────────┘                         └────────────────────┘
```

### What Adobe Auto-Tag Fixes

| Issue | Before | After |
|-------|--------|-------|
| Tagged PDF | ❌ No `/StructTreeRoot` | ✅ Full structure tree |
| Heading Hierarchy | ❌ Flat text | ✅ `/H1`, `/H2`, `/H3` with proper nesting |
| Tables | ❌ Raw text | ✅ `/Table`, `/TR`, `/TH` (scope), `/TD` |
| Lists | ❌ Unstructured | ✅ `/L`, `/LI`, `/Lbl`, `/LBody` |
| Reading Order | ❌ Unknown | ✅ `/ParentTree` mapping |
| Image Alt Text | ❌ Missing | ✅ `/Figure` with `/Alt` (generated) |
| Links | ❌ Untagged | ✅ `/Link` with `/LinkObjr` |

### What Still Needs Human Review

Adobe auto-tag handles ~90% of structural issues. The remaining checks need manual review:

- **Alt text quality** — Adobe generates descriptions; verify accuracy for images/charts
- **Reading order** — Multi-column layouts may need order adjustment
- **Color contrast** — Not auto-fixable; requires source document edit
- **Complex table headers** — Nested headers may need manual scope assignment

### Adobe API Cost

- **Free tier:** 500 PDF operations/month
- **Standard:** ~$0.05 per auto-tag operation
- [Pricing details](https://developer.adobe.com/document-services/pricing/)

## Project Architecture

```
pdf-cleanse-ada/
├── server.js                 # Express server (port 3456)
├── index.html                # Web UI (dark theme, drag-drop, SSE terminal)
├── pdf-tools.js              # Node.js PDF pipeline (upload → fix → sort)
├── pdf_fix_single.py         # Python metadata fixer (stdin/stdout pipe)
├── compliance_checker.py     # Deep WCAG/PDF-UA/508 checker (1200+ lines)
├── deep_scan.py              # Batch compliance scan API
├── adobe_autotag_api.py      # Adobe Cloud API client (upload → tag → download)
├── adobe_auto.py             # Adobe Acrobat COM automation (local)
├── batch_auto_tag.py         # Batch COM auto-tag (local Acrobat)
├── pipeline.py               # CLI pipeline runner
│
├── input_pdfs/               # ← Drop PDFs here
├── done/                     # ✓ Compliant (metadata fixed, tagged)
├── needs_review/             # ⚠ Needs Adobe auto-tag
├── adobe_tagged/             # ← Adobe Cloud tagged PDFs land here
├── auto_fixed/               # Python auto-fix intermediate
├── adobe_fixed/              # Adobe COM fix intermediate
├── pipeline_results/         # CSV reports
└── assessment_results/       # Deep scan reports
```

## Pain Points & Lessons Learned

See `specs/standards/` for detailed documentation of each issue and its fix:

| # | Standard | Topic |
|---|----------|-------|
| 001 | [pdf-lib catalog access](specs/standards/001-pdf-lib-catalog-access.md) | Switched to pikepdf for catalog modifications |
| 002 | [pikepdf traversal safety](specs/standards/002-pikepdf-traversal-safety.md) | `_is_array()`/`_is_dict()` defensive helpers |
| 003 | [Adobe auto-tag API](specs/standards/003-adobe-autotag-api.md) | Cloud API primary, COM fallback |
| 004 | [URL filename resolution](specs/standards/004-url-filename-resolution.md) | Dual search with `decodeURIComponent` |
| 005 | [Playwright MCP](specs/standards/005-playwright-mcp.md) | Browser automation testing |
| 006 | [Raw binary scanning](specs/standards/006-raw-binary-scanning.md) | Regex detection for pdf-lib blind spots |
| 007 | [Pipeline sort logic](specs/standards/007-pipeline-sort-logic.md) | Zero auto-fixable = compliant |

Full architecture diagrams in [`specs/spec.md`](specs/spec.md).

## Documentation

All documentation lives in one of these locations (per [`specs/doc_policy.md`](specs/doc_policy.md)):

| File | Content |
|------|---------|
| `README.md` | This file — overview, quick start, API reference |
| `CHANGELOG.md` | Chronological change history |
| [`specs/spec.md`](specs/spec.md) | Architecture diagrams (ASCII art) |
| [`specs/tasks.md`](specs/tasks.md) | Task tracker |
| [`specs/plan.md`](specs/plan.md) | Project plan and risk register |
| [`specs/doc_policy.md`](specs/doc_policy.md) | Documentation policy |
| [`specs/standards/`](specs/standards/) | Numbered standards (pain points + fixes) |

## Compliance Standards

### WCAG 2.2
| Criteria | Name | Level |
|----------|------|-------|
| 2.4.2 | Page Titled | A |
| 3.1.1 | Language of Page | A |
| 1.3.1 | Info and Relationships | A |
| 1.1.1 | Non-text Content | A |
| 1.3.2 | Meaningful Sequence | A |
| 2.4.6 | Headings and Labels | AA |
| 1.4.3 | Contrast (Minimum) | AA |

### PDF/UA-1 (ISO 14289-1)
| Section | Requirement |
|---------|-------------|
| §5 | Tagged PDF structure |
| §5.3 | MarkInfo and reading order |
| §5.4 | Heading hierarchy |
| §5.5 | List structure |
| §5.6 | Figure alt text |
| §5.7 | Table headers |
| §7.1 | Document title |
| §7.2 | Document language |

### Section 508
| Criteria | Description |
|----------|-------------|
| 502.3.1 | Metadata and security |
| 502.3.2 | Tagged PDF structure |
| 502.3.3 | Alternative text |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/terminal-stream` | SSE terminal output stream |
| `POST` | `/api/setup` | Install dependencies |
| `POST` | `/api/upload` | Upload PDF(s) |
| `GET` | `/api/files` | List uploaded PDFs |
| `POST` | `/api/process` | Run metadata fix pipeline |
| `POST` | `/api/adobe-autotag` | Run Adobe Cloud auto-tag |
| `POST` | `/api/deep-scan` | Run deep compliance scan |
| `POST` | `/api/auto-tag` | Open PDF in Acrobat (COM) |
| `POST` | `/api/re-assess` | Re-check compliance on single PDF |
| `GET` | `/api/report/latest` | Download latest CSV report |
| `GET` | `/api/results/:type/:name` | Download result PDF |

## Requirements

- **Node.js** 18+
- **Python** 3.10+
- **Adobe PDF Services credentials** (for cloud auto-tag) — optional
- **Adobe Acrobat Pro** (for local COM auto-tag) — optional

```
npm packages: pdf-lib, express, multer
Python packages: pikepdf>=9.0.0, Pillow>=10.0.0, requests>=2.31.0, pywin32>=306
```
