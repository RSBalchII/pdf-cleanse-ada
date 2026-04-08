# Architecture Specification

Visual documentation of the PDF ADA Compliance Processor architecture.

---

## System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        PDF ADA Compliance Processor                         │
│                          http://localhost:3456                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌─────────────┐    ┌────────────────    ┌────────────  │
│  │  Upload  │───►│   Process   │───►│  Adobe Cloud   │───►│  Re-Assess │  │
│  │ PDFs     │    │  (Metadata) │    │  Auto-Tag      │    │  & Sort    │  │
│  └──────────    └─────────────┘    └────────────────    └────────────┘  │
│       │                │                    │                    │          │
│       ▼                ▼                    ▼                    ▼          │
│  input_pdfs/      done/ or            adobe_tagged/       CSV Report      │
│                   needs_review/                            + JSON          │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Web Server (server.js)                       │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Express.js (port 3456)                                            │  │
│  │                                                                     │  │
│  │  Routes:                                                            │  │
│  │  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │  │ GET  /                  →  index.html (UI)                 │   │  │
│  │  │ GET  /terminal-stream   →  SSE event stream                 │   │  │
│  │  │ POST /api/upload        →  Multer file upload               │   │  │
│  │  │ GET  /api/files         →  List input_pdfs/                │   │  │
│  │  │ POST /api/process       →  Run metadata pipeline            │   │  │
│  │  │ POST /api/adobe-autotag →  Run Adobe Cloud auto-tag         │   │  │
│  │  │ POST /api/deep-scan     →  Python compliance checker        │   │  │
│  │  │ POST /api/re-assess     →  Re-check single PDF              │   │  │
│  │  │ GET  /api/report/latest →  Download CSV                     │   │  │
│  │  └─────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                  │                                         │
│                          ┌───────┴───────┐                                │
│                          ▼               ▼                                │
│              ┌──────────────────┐  ┌──────────────────┐                   │
│              │  pdf-tools.js    │  │  Python Scripts  │                   │
│              │  (Node.js)       │  │  (Subprocess)    │                   │
│              │                  │  │                  │                   │
│              │  • readPdfInfo() │  │  pdf_fix_single. │                   │
│              │  • checkCompli.  │  │  py              │                   │
│              │  • fixPdf() ────┼──┼─► stdin/stdout   │                   │
│              │  • processPdf()  │  │                  │                   │
│              │  • generateCsv() │  │  compliance_     │                   │
│              └──────────────────┘  │  checker.py      │                   │
│                                    │                  │                   │
│                                    │  adobe_autotag_  │                   │
│                                    │  api.py          │                   │
│                                    └──────────────────┘                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## PDF Processing Pipeline

```
                      ┌─────────────────────────┐
                      │   Input PDF (raw bytes)  │
                      └────────────┬─────────────┘
                                   │
                      ┌────────────▼─────────────┐
                      │  Step 1: Read Metadata    │
                      │  ┌────────────────────┐   │
                      │  │ pdf-lib:           │   │
                      │  │  • getTitle()      │   │
                      │  │  • getPageCount()  │   │
                      │  ├────────────────────┤   │
                      │  │ Raw binary scan:   │   │
                      │  │  • /StructTreeRoot │   │
                      │  │  • /MarkInfo       │   │
                      │  │  • /Lang           │   │
                      │  │  • /ParentTree     │   │
                      │  │  • /Figure, /TH... │   │
                      │  └────────────────────┘   │
                      └────────────┬─────────────┘
                                   │
                      ┌────────────▼─────────────┐
                      │  Step 2: Compliance Check │
                      │  ┌────────────────────┐   │
                      │  │ Issues identified: │   │
                      │  │  CRITICAL (fixable)│   │
                      │  │  CRITICAL (manual) │   │
                      │  │  IMPORTANT         │   │
                      │  │  ADVISORY          │   │
                      │  └────────────────────┘   │
                      └────────────┬─────────────┘
                                   │
                      ┌────────────▼─────────────┐
                      │  Step 3: Auto-Fix         │
                      │  ┌────────────────────┐   │
                      │  │ Python/pikepdf:    │   │
                      │  │  • Set /Title      │   │
                      │  │  • Set /Lang       │   │
                      │  │  • Set MarkInfo    │   │
                      │  │  • Set DisplayDoc  │   │
                      │  └────────────────────┘   │
                      └────────────┬─────────────┘
                                   │
                      ┌────────────▼─────────────┐
                      │  Step 4: Re-Assess        │
                      │  ┌────────────────────┐   │
                      │  │ Re-check compliance│   │
                      │  │ on fixed PDF       │   │
                      │  └────────────────────┘   │
                      └────────────┬─────────────┘
                                   │
                          ┌───────┴───────┐
                          │ auto-fixable  │
                          │ issues = 0?   │
                          └───┬───────┬───┘
                              │ Yes   │ No
                              ▼       ▼
                    ┌─────────────┐ ┌─────────────┐
                    │   done/     │ │needs_review/│
                    │  (compliant)│ │  (needs tag)│
                    └─────────────┘ └──────┬──────┘
                                           │
                              ┌────────────▼────────────┐
                              │  Step 5: Adobe Cloud    │
                              │  Auto-Tag               │
                              │  ┌──────────────────┐   │
                              │  │ Upload → Tag →   │   │
                              │  │ Download         │   │
                              │  └──────────────────┘   │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────┐
                              │  adobe_tagged/      │
                              │  (fully tagged PDF) │
                              └─────────────────────┘
```

---

## Adobe Cloud API Flow

```
  Local Machine                              Adobe Cloud Services
  ┌──────────────────────────┐               ┌──────────────────────────┐
  │                          │               │                          │
  │  adobe_autotag_api.py    │               │  Adobe IMS               │
  │  ┌────────────────────┐  │               │  ┌────────────────────┐  │
  │  │ 1. Authenticate    │  │               │  │ POST /ims/token/v3 │  │
  │  │    client_id +     ├──┼──────────────►│  │ {client_id, secret}│  │
  │  │    client_secret   │  │               │  └──────────┬─────────┘  │
  │  └────────────────────┘  │               │             │            │
  │                          │               │  ┌──────────▼─────────┐  │
  │  ┌────────────────────┐  │               │  │ 200 {access_token} │  │
  │  │ 2. Upload Asset    │  │               │  │ expires_in: 86400  │  │
  │  │    POST /assets    ├──┼──────────────►│  └────────────────────┘  │
  │  │    {mediaType}     │  │               │                          │
  │  └────────────────────┘  │               │  Adobe Asset Storage     │
  │           │              │               │  ┌────────────────────┐  │
  │  ┌────────▼────────────┐ │               │  │ PUT presigned URL  │  │
  │  │ 3. Direct PUT to    │ │               │  │ (S3 backend)       │  │
  │  │    presigned URL     ├─┼──────────────►│  │ 200 OK             │  │
  │  └─────────────────────┘ │               │  └────────────────────┘  │
  │           │              │               │                          │
  │  ┌────────▼────────────┐ │               │  Auto-Tag Engine (ML)    │
  │  │ 4. Submit Auto-Tag  │ │               │  ┌────────────────────┐  │
  │  │    POST /operation/  │ │               │  │ ML model analyzes: │  │
  │  │    /autotag          ├──┼──────────────►│  │  • Headings (H1-H6)│  │
  │  │    {assetID}         │ │               │  │  • Tables (TH/TD)  │  │
  │  └─────────────────────┘ │               │  │  • Lists (L/LI)    │  │
  │           │              │               │  │  • Figures (/Alt)   │  │
  │  ┌────────▼────────────┐ │               │  │  • Reading order    │  │
  │  │ 5. Poll Status      │ │               │  │  • Links            │  │
  │  │    GET /autotag/     │ │               │  └──────────┬─────────┘  │
  │  │    {jobID}/status    ◄─┼───────────────┤             │            │
  │  │    every 15s         │ │               │  ┌──────────▼─────────┐  │
  │  └─────────────────────┘ │               │  │ {status: "done"}   │  │
  │           │              │               │  └────────────────────┘  │
  │  ┌────────▼────────────┐ │               │                          │
  │  │ 6. Download         │ │               │  Asset Download          │
  │  │    GET /assets/      │ │               │  ┌────────────────────┐  │
  │  │    {assetID}         ├─┼──────────────►│  │ GET presigned URL  │  │
  │  └─────────────────────┘ │               │  │ 200 PDF bytes      │  │
  │           │              │               │  └────────────────────┘  │
  │  ┌────────▼────────────┐ │               │                          │
  │  │ 7. Verify & Save    │ │               │                          │
  │  │    pikepdf check     │ │               │                          │
  │  │    /StructTreeRoot   │ │               │                          │
  │  │    → adobe_tagged/   │ │               │                          │
  │  └─────────────────────┘ │               │                          │
  │                          │               │                          │
  └──────────────────────────┘               └──────────────────────────┘
```

---

## Data Flow

```
  User Browser                              Server                        Filesystem
  ┌──────────────┐                          ┌──────────────┐             ┌──────────────┐
  │              │                          │              │             │              │
  │  Drag-drop   │──── PDF files ──────────►│  Multer      │────────────►│ input_pdfs/  │
  │  or Browse   │                          │  (save)      │             │              │
  │              │◄──── {success} ──────────│              │             │              │
  │              │                          │              │             │              │
  │  Click       │──── POST /api/process ──►│  processPdf()│             │              │
  │  Process     │                          │  ┌─────────┐ │             │              │
  │              │◄──── SSE stream ──────────┼─►│readInfo │ │             │              │
  │  Terminal    │   (real-time)            │  │check    │ │             │              │
  │  output      │                          │  │fix(py)  │─┼──subprocess─┤ done/        │
  │              │                          │  │re-assess│ │   pipe      │ or           │
  │  Results     │◄──── JSON results ───────│  └─────────┘ │             │ needs_review/│
  │  table       │                          │              │             │              │
  │              │                          │              │             │              │
  │  Click       │──── POST /api/adobe-     │  adobe_      │             │              │
  │  Adobe Cloud │      autotag             │  autotag_    │────────────►│ adobe_tagged/│
  │  Auto-Tag    │                          │  api.py      │             │              │
  │              │◄──── SSE stream ──────────│  (REST API) │◄────────────│              │
  │              │                          │              │   Adobe Cloud              │
  │  Click       │──── POST /api/re-assess ─│  compliance_ │             │              │
  │  Re-Assess   │                          │  checker.py  │────────────►│ any dir      │
  │              │◄──── before/after ───────│              │             │              │
  │              │                          │              │             │              │
  │  Download    │──── GET /api/report/     │  CSV file    │────────────►│ pipeline_    │
  │  CSV Report  │      latest              │  stream      │             │ results/     │
  │              │                          │              │             │              │
  └──────────────┘                          └──────────────┘             └──────────────┘
```

---

## File Type Classification

```
  PDF Types in the Pipeline

  ┌───────────────────────────────────────────────────────────────────┐
  │  1. Untagged PDF (input)                                          │
  │     ✗ No /StructTreeRoot                                          │
  │     ✗ No /Lang                                                    │
  │     ✗ No /Title (or filename as title)                            │
  │     ✗ No MarkInfo.Marked                                          │
  │     → Goes through: metadata fix → Adobe auto-tag                  │
  ├───────────────────────────────────────────────────────────────────┤
  │  2. Metadata-Fixed PDF (done/)                                    │
  │     ✓ /Title set                                                  │
  │     ✓ /Lang set (en-US)                                           │
  │     ✓ MarkInfo.Marked = true                                      │
  │     ✓ DisplayDocTitle = true                                      │
  │     ✗ No /StructTreeRoot (still untagged)                         │
  │     → Needs Adobe auto-tag for full compliance                     │
  ├───────────────────────────────────────────────────────────────────┤
  │  3. Adobe-Tagged PDF (adobe_tagged/)                              │
  │     ✓ /Title set                                                  │
  │     ✓ /Lang set                                                   │
  │     ✓ MarkInfo.Marked = true                                      │
  │     ✓ /StructTreeRoot present                                     │
  │     ✓ /ParentTree present (reading order)                         │
  │     ✓ /H1-/H6 headings (if detected)                              │
  │     ✓ /Table, /TR, /TH, /TD (if tables detected)                  │
  │     ✓ /Figure with /Alt (if images detected)                      │
  │     → Fully compliant (pending human review of alt text quality)  │
  └───────────────────────────────────────────────────────────────────┘
```

---

## Issue Severity Classification

```
  Issue Levels and Sort Impact

  ┌─────────────┬──────────────┬──────────────────────────────────────┐
  │  Severity   │  Auto-Fix?   │  Sort Impact                         │
  ├─────────────┼──────────────┼──────────────────────────────────────┤
  │  CRITICAL   │  Yes         │  → needs_review/ (pipeline bug)      │
  │             │              │    Title, Lang, MarkInfo, DisplayDoc  │
  ├─────────────┼──────────────┼──────────────────────────────────────┤
  │  CRITICAL   │  No (Adobe)  │  → done/ (then auto-tag)             │
  │             │              │    No StructTreeRoot                  │
  ├─────────────┼──────────────┼──────────────────────────────────────┤
  │  IMPORTANT  │  No          │  → done/ (informational)             │
  │             │              │    Missing ParentTree                 │
  ├─────────────┼──────────────┼──────────────────────────────────────┤
  │  ADVISORY   │  No          │  → done/ (informational)             │
  │             │              │    No bookmarks, large doc            │
  └─────────────┴──────────────┴──────────────────────────────────────┘

  Sort decision: auto-fixable count > 0 ? needs_review/ : done/
```
