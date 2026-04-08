# Project Plan

## Current Phase: Adobe Cloud Auto-Tag Integration

**Goal:** Programmatically auto-tag all untagged PDFs using Adobe's official PDF Services API, achieving full WCAG/PDF-UA/Section 508 compliance with minimal human intervention.

**Status:** Infrastructure built, awaiting credentials to run.

---

## Phase 1: Metadata Auto-Fix ✅ COMPLETE

**What:** Fix PDF catalog-level metadata that can be programmatically set.

**Done:**
- Python/pikepdf subprocess pipeline (title, language, MarkInfo, DisplayDocTitle)
- Raw binary scanner for detection (pdf-lib can't expose these)
- Compliance checker with 15+ checks mapped to WCAG/PDF-UA/508
- Web UI with drag-drop, SSE streaming, results table
- Sort logic: done/ vs needs_review/

**Result:** 13/19 PDFs fully compliant, 6/19 need structural tagging.

---

## Phase 2: Structural Auto-Tagging 🔄 IN PROGRESS

**What:** Use Adobe Cloud API to add structure trees to untagged PDFs.

**Infrastructure Built:**
- `adobe_autotag_api.py` — Full Adobe API client (auth, upload, tag, download)
- Server endpoint `/api/adobe-autotag` — Web UI integration
- UI button ☁️ Adobe Cloud Auto-Tag
- Post-tagging verification via pikepdf
- `adobe_tagged/` output directory

**Awaiting:** Adobe Developer credentials (client_id + client_secret)

**Estimated Runtime:** 2-5 minutes per PDF × 6 PDFs = 12-30 minutes

---

## Phase 3: Verification & Reporting ⏳ PENDING

**What:** Verify tagged PDFs pass accessibility checks and generate final report.

**Steps:**
1. Run Acrobat Accessibility Checker on each `adobe_tagged/` PDF
2. Record pass/fail counts per PDF
3. Generate Excel report with before/after comparison
4. Identify remaining human-review items (alt text quality, reading order)
5. Deliver cleaned PDFs + report

**Expected Outcome:** ~90% of issues auto-resolved, ~10% require manual review.

---

## Phase 4: Production Deployment ⏳ PENDING

**What:** Package and deploy for ongoing use.

**Steps:**
1. Dockerize the application
2. Set up CI/CD with Playwright MCP tests
3. Document credential management
4. Create user guide for non-technical users

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Python/pikepdf over pdf-lib for catalog mods | pdf-lib cannot reliably write MarkInfo, ViewerPreferences, StructTreeRoot |
| Adobe Cloud API over COM automation | COM is unreliable (async, no callbacks, silent crashes, visibility required) |
| Zero auto-fixable = "done" | Human-review issues are not failures; they require judgment by definition |
| Raw binary scanning for detection | pdf-lib hides catalog entries; regex on binary buffer works reliably |
| pikepdf `_is_array`/`_is_dict` helpers | pikepdf types don't match Python list/dict; `.get()` throws on Array |
| Playwright MCP for testing | Manual browser testing doesn't scale with iterative development |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Adobe API credentials expire | Medium | Token auto-refresh built in; credentials saved to file |
| Adobe auto-tag generates poor alt text | Low | Human review step; alt text can be edited in Acrobat |
| Large PDFs timeout on Adobe API | Low | 600s timeout; most PDFs complete in 2-5 min |
| API cost exceeds budget | Low | Free tier: 500 ops/month; 6 PDFs = 6 ops |
| pikepdf version incompatibility | Low | Pinned `>=9.0.0`; tested on current version |
