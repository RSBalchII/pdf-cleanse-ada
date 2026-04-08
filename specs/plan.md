# Project Plan

## Current Phase: Final Delivery

**Goal:** Deliver all 19 PDFs with full ADA compliance, document the process, and establish repeatable workflow.

**Status:** 19/19 PDFs processed. 13 fully compliant, 6 need Acrobat Pro Auto-Tag.

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

## Phase 2: Structural Auto-Tagging ✅ PARTIALLY COMPLETE

**What:** Use Adobe Cloud API to add structure trees to untagged PDFs.

**Findings:**
- ✅ Adobe Cloud API works correctly (auth, upload, tag, download all functional)
- ✅ 4 PDFs successfully auto-tagged with full structure tree
- ⚠️ Free tier quota exhausted after initial batch
- ⚠️ Acrobat Pro COM auto-tag blocked by Acrobat security (cannot trigger `TouchUp_AutoTag` programmatically)

**Remaining:**
- 6 PDFs need Acrobat Pro Auto-Tag via UI (Action Wizard recommended for batch)
- No code changes needed — Acrobat Pro Action Wizard handles this

---

## Phase 3: Verification & Reporting ⏳ IN PROGRESS

**What:** Verify tagged PDFs pass accessibility checks and generate final report.

**Completed:**
- All 4 Cloud-tagged PDFs verified with pikepdf (StructTreeRoot present, Lang set, Marked=true)
- All 19 PDFs copied to `Downloads/ADA_Cleaned/`
- CSV reports generated in `pipeline_results/`

**Remaining:**
- [ ] Re-assess all 19 PDFs after remaining 6 get Auto-Tagged via Acrobat Pro
- [ ] Generate final Excel report with before/after comparison

---

## Phase 4: Production Documentation ⏳ IN PROGRESS

**What:** Document the complete workflow for ongoing use.

**Completed:**
- README.md with full documentation
- CHANGELOG.md with chronological change history
- `specs/standards/` — 7 numbered standards
- `specs/spec.md` — Architecture diagrams
- `specs/doc_policy.md` — Documentation policy

**Remaining:**
- [ ] Add Acrobat Pro Action Wizard guide
- [ ] Add user guide for non-technical operators

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Python/pikepdf over pdf-lib for catalog mods | pdf-lib cannot reliably write MarkInfo, ViewerPreferences, StructTreeRoot |
| Adobe Cloud API over COM automation | COM is blocked by Acrobat security; Cloud API works but has quota |
| Credentials file over OAuth | Simpler for single-user setup; OAuth adds complexity with no benefit for this use case |
| Zero auto-fixable = "done" | Human-review issues are not failures; they require judgment by definition |
| Raw binary scanning for detection | pdf-lib hides catalog entries; regex on binary buffer works reliably |
| pikepdf `_is_array`/`_is_dict` helpers | pikepdf types don't match Python list/dict; `.get()` throws on Array |
| Playwright MCP for testing | Manual browser testing doesn't scale with iterative development |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Adobe Cloud API quota exhausted | Medium | Use Acrobat Pro Action Wizard (unlimited, local) |
| Acrobat Pro trial expires (6 days) | High | Purchase license or use Cloud API when quota resets |
| Adobe auto-tag generates poor alt text | Low | Human review step; alt text can be edited in Acrobat |
| Large PDFs timeout on Adobe API | Low | 600s timeout; most PDFs complete in 2-5 min |
| API cost exceeds budget | Low | Free tier: 500 ops/month; Acrobat Pro Action Wizard is unlimited |
| pikepdf version incompatibility | Low | Pinned `>=9.0.0`; tested on current version |
