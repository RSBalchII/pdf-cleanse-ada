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

---

## In Progress

- [ ] **T013** — Run Adobe Cloud Auto-Tag on 6 untagged PDFs in `needs_review/`
  - Requires: Adobe Developer credentials (client_id + client_secret)
  - Estimated: 2-5 minutes per PDF

---

## Planned

- [ ] **T014** — Verify Adobe-tagged PDFs pass Acrobat Accessibility Checker
  - Open each PDF in `adobe_tagged/` in Acrobat
  - Run `Tools > Accessibility > Full Check`
  - Record pass/fail counts
- [ ] **T015** — Generate final Excel report with all cleaned PDFs
  - Include: filename, status, issues fixed, remaining issues
  - Copy to `Downloads/ADA_Cleaned/`
- [ ] **T016** — Add alt-text quality review workflow
  - Adobe auto-tag generates alt text — verify accuracy for charts/images
  - Flag PDFs where generated alt text needs correction
- [ ] **T017** — Add batch re-assess after Adobe tagging
  - Run compliance checker on all `adobe_tagged/` PDFs
  - Generate comparison report: before Adobe vs after Adobe
- [ ] **T018** — CI/CD pipeline for automated testing
  - Run Playwright MCP tests on push
  - Verify UI loads, pipeline runs, results display correctly

---

## Backlog

- [ ] **T019** — Add OCR support for scanned/image-only PDFs
- [ ] **T020** — Add support for multi-language documents (`/Lang` per section)
- [ ] **T021** — Add bookmark generation for large documents (21+ pages)
- [ ] **T022** — Add color contrast checker (manual check guidance)
- [ ] **T023** — Dockerize the application for easy deployment
