# Task Tracker

Current and upcoming tasks for the PDF ADA Compliance Processor.

---

## Completed

- [x] **T001** — Build Express web server with SSE terminal streaming (port 3456)
- [x] **T002** — Implement Python/pikepdf metadata fixer via stdin/stdout pipe
- [x] **T003** — Add deep compliance checker (WCAG/PDF-UA/508, 1200+ lines)
- [x] **T004** — Add Adobe Cloud API auto-tag integration
- [x] **T005** — Add Re-Assess endpoint with before/after comparison
- [x] **T006** — Fix pikepdf array handling (`_is_array`/`_is_dict` helpers)
- [x] **T007** — Fix URL-encoded filename resolution across all endpoints
- [x] **T008** — Add Playwright MCP for browser automation
- [x] **T009** — Document all pain points in `specs/standards/`
- [x] **T010** — Initialize git repository with `.gitignore`
- [x] **T011** — Update README with full documentation
- [x] **T012** — Establish documentation policy (`specs/doc_policy.md`)
- [x] **T013** — Run Adobe Cloud Auto-Tag on PDFs
  - Result: 4/19 succeeded (quota exhausted), 15 failed (QUOTA_EXCEEDED)
- [x] **T014** — Verify Adobe-tagged PDFs pass pikepdf verification
  - All 4 tagged PDFs confirmed: StructTreeRoot present, Lang set, Marked=true
- [x] **T015** — Generate final delivery with all cleaned PDFs
  - All 19 PDFs copied to `Downloads/ADA_Cleaned/`
- [x] **T016** — Fix Windows console emoji encoding in Python scripts
- [x] **T017** — Simplify server: remove OAuth, use direct credentials
- [x] **T018** — Test Acrobat Pro COM auto-tag (confirmed blocked by security)
- [x] **T019** — Add `--auto` flag for non-interactive batch mode
- [x] **T020** — Update documentation per doc_policy

---

## In Progress

- [ ] **T021** — Complete auto-tag for remaining 6 PDFs
  - Options: Acrobat Pro Action Wizard (unlimited) or manual Auto-Tag per PDF
  - 6 untagged PDFs: those in `needs_review/` that Cloud API couldn't process

---

## Planned

- [ ] **T022** — Add Acrobat Pro Action Wizard guide to README
  - Step-by-step instructions for batch auto-tag via Acrobat Pro UI
  - No quota limits, uses local Acrobat Pro installation
- [ ] **T023** — Add batch re-assess after all PDFs are fully tagged
  - Run compliance checker on all 19 PDFs
  - Generate final comparison report: before vs after full pipeline
- [ ] **T024** — Add alt-text quality review workflow
  - Adobe auto-tag generates alt text — verify accuracy for charts/images
  - Flag PDFs where generated alt text needs correction
- [ ] **T025** — Add bookmark generation for large documents (21+ pages)
- [ ] **T026** — Dockerize the application for easy deployment

---

## Backlog

- [ ] **T027** — Add OCR support for scanned/image-only PDFs
- [ ] **T028** — Add support for multi-language documents (`/Lang` per section)
- [ ] **T029** — Add color contrast checker (manual check guidance)
- [ ] **T030** — CI/CD pipeline for automated testing with Playwright MCP
