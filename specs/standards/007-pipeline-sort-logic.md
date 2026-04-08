# Standard 007: Pipeline Sort Logic — When Is a PDF "Done"?

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** `pdf-tools.js`, `server.js`, `index.html`

## Pain Point

After running metadata fixes, a PDF may have remaining issues that fall into two categories:
- **Auto-fixable** — The pipeline could fix it but didn't (a bug)
- **Human-review** — Genuinely requires human judgment (alt text quality, reading order in multi-column layouts, color contrast)

If a PDF has 0 auto-fixable issues but 2 human-review issues, should it be sorted to `done/` or `needs_review/`?

The initial approach blocked "done" status on ANY remaining issue, meaning PDFs with only human-review items never reached "compliant" status.

## Root Cause

Conflating "auto-fixable" and "human-review" issues in the sort decision. Human-review issues are not failures — they are items that require manual inspection by definition.

## Fix Applied

A PDF is **"done"** (sorted to `done/`) when it has **zero auto-fixable issues**, regardless of remaining human-review issues:

```javascript
const autoFixable = issuesAfter.filter(i => i.fixable).length;
const needsReview = autoFixable > 0;
const destDir = needsReview ? NEEDS_REVIEW_DIR : DONE_DIR;
```

Issue severity levels in the compliance checker:
- `CRITICAL` — Must be fixed (auto-fixable if metadata, human-review if structural)
- `IMPORTANT` — Should be fixed (may be auto-fixable or human-review)
- `ADVISORY` — Nice to have (always human-review, e.g., bookmarks)

## Definitive Standard

**Rule 1:** A PDF is "compliant" (sorted to `done/`) when it has **zero auto-fixable issues**, even if human-review issues remain.

**Rule 2:** A PDF is "needs review" (sorted to `needs_review/`) when it has **one or more auto-fixable issues** that the pipeline failed to fix.

**Rule 3:** Human-review issues are informational only and do NOT block "compliant" status. They are reported in the terminal output and CSV for awareness.

**Rule 4:** The `fixable` flag on each issue determines sort destination:
- `fixable: true` + still present after fixes → `needs_review/`
- `fixable: false` → reported but does not affect sort

**Rule 5:** The compliance summary MUST clearly distinguish:
- Issues that should have been auto-fixed (pipeline bug)
- Issues that require Adobe auto-tag (structural)
- Issues that require human review (quality judgment)

## Related Standards

- Standard 001 (auto-fixable metadata fixes)
- Standard 003 (structural fixes via Adobe)

## References

- `pdf-tools.js` → `processPdf()` — Sort logic implementation
- `pdf-tools.js` → `checkCompliance()` — Issue `fixable` flag assignment
