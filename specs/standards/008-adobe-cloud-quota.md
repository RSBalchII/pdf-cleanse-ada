# Standard 008: Adobe Cloud API Quota Limits

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** `adobe_autotag_api.py`, `server.js`

## Pain Point

Adobe Cloud API free tier quota for PDF Services API is limited. After processing 4 PDFs via the auto-tag endpoint, all subsequent requests returned:

```
429 QUOTA_EXCEEDED: "Either quota for this operation is not available or Free Tier quota is exhausted."
```

This occurs even when the Adobe account shows "PDF Services API" as included in the plan. The Auto-Tag API has a separate, tighter quota than general PDF Services operations.

## Root Cause

Adobe's PDF Services API has two quota systems:
1. **General PDF operations** (combine, compress, export, etc.) — 500/month free tier
2. **Auto-Tag API** — much tighter limit, quota exhausted after ~4-10 operations

The free trial credits are shared but Auto-Tag operations consume credits faster than documented.

## Fix Applied

**No code fix needed** — the API client works correctly. Instead, we added:

1. **Graceful degradation:** When quota is exhausted, the pipeline continues processing remaining PDFs and reports failures clearly.
2. **Alternative path:** Acrobat Pro Action Wizard provides unlimited local auto-tagging with no quota limits.
3. **Non-interactive mode:** Added `--auto` flag to `adobe_autotag_api.py` for batch processing.

## Definitive Standard

**Rule 1:** Adobe Cloud API should be used as the **primary** auto-tag method when quota is available.

**Rule 2:** When quota is exhausted, fall back to **Acrobat Pro Action Wizard** for unlimited local auto-tagging.

**Rule 3:** The pipeline MUST handle 429 QUOTA_EXCEEDED gracefully:
- Log the error clearly
- Continue processing remaining PDFs (don't abort the batch)
- Report which PDFs succeeded vs failed
- Save partial results (successfully tagged PDFs are still valuable)

**Rule 4:** Always copy successfully processed PDFs to the output directory, even if the batch partially failed.

## Related Standards

- Standard 003 (Adobe auto-tag API)
- Standard 007 (Pipeline sort logic)

## References

- `adobe_autotag_api.py` — Adobe Cloud API client with quota handling
- `adobe_tagged/adobe_auto_tag_report.json` — Batch results report
