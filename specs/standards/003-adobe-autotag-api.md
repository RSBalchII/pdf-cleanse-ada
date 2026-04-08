# Standard 003: Adobe Auto-Tag — Cloud API Primary, COM Blocked

**Date:** 2026-04-07 (updated)
**Status:** DEFINITIVE
**Components Affected:** `adobe_autotag_api.py`, `adobe_auto.py`, `batch_auto_tag_acrobat.py`, `server.js`

## Pain Point

Initial attempts to auto-tag PDFs using **Adobe Acrobat Pro COM automation** (`win32com.client`) were **blocked by Acrobat's security design**:

1. **`TouchUp_AutoTag` cannot be triggered programmatically:** Both `app.execMenuItem()` and `jso.runMenuItem()` throw exceptions when called on the Auto-Tag menu item.
2. **COM threading:** Python's COM automation requires `pythoncom.CoInitialize()` and `CoUninitialize()` per thread.
3. **No result extraction:** Adobe's COM API does not expose accessibility checker results programmatically.
4. **Acrobat must be running:** COM requires an active Acrobat Pro instance (not Reader).

This is a deliberate security restriction by Adobe — Auto-Tag requires user interaction.

**Additionally**, Adobe Cloud API free tier quota is limited (see Standard 008). After ~4 operations, subsequent requests return `429 QUOTA_EXCEEDED`.

## Root Cause

Adobe Acrobat's COM API was designed for **document viewing and printing**, not programmatic batch processing. The accessibility features are UI-driven and not exposed through COM interfaces.

## Fix Applied

Built **Adobe Cloud API integration** (`adobe_autotag_api.py`) as the primary auto-tag path:

```
Local Machine                          Adobe Cloud
┌───────────────┐                      ┌──────────────────┐
│               │  1. POST /ims/token  │                  │
│  Client ID +  │ ───────────────────► │  Adobe IMS Auth  │
│  Secret       │  2. access_token     │                  │
└───────┬───────┘                      └──────────────────┘
        │
        │  3. POST /assets → 4. {assetID, uploadUri}
        │  5. PUT presigned URL → 6. 200 OK
        │  7. POST /operation/autotag → 8. jobID
        │  9. Poll every 15s → 10. {status: "done"}
        │  11. GET /assets/{id} → 12. {downloadUri}
        │  13. GET downloadUri → 14. PDF bytes
        ▼
  Save to adobe_tagged/
```

**COM automation** is retained in `adobe_auto.py` for reference but **cannot auto-tag programmatically**.

**For remaining PDFs after quota exhaustion:** Use Acrobat Pro **Action Wizard** (unlimited, no quota):
1. `Tools > Action Wizard > New Action`
2. Add "Make Accessible" step
3. Run on folder of PDFs

## Definitive Standard

**Rule 1:** The **primary** auto-tag path is Adobe Cloud API (`adobe_autotag_api.py`). This is the default in the web UI.

**Rule 2:** COM automation (`adobe_auto.py`, `batch_auto_tag_acrobat.py`) **cannot trigger Auto-Tag programmatically**. It is retained for document open/close operations only.

**Rule 3:** When Cloud API quota is exhausted, use **Acrobat Pro Action Wizard** for unlimited local auto-tagging.

**Rule 4:** The Adobe API client MUST implement:
- Token management with auto-refresh (check expiry, refresh at 60s before expiry)
- Session-based requests with persistent `x-api-key` and `Authorization: Bearer` headers
- Two-step upload: `POST /assets` → `PUT` to presigned URL
- Job polling with configurable timeout (default 600s) and interval (default 15s)
- Two-step download: `GET /assets/{id}` → `GET downloadUri`
- Post-download verification: verify `/StructTreeRoot` exists using pikepdf

**Rule 5:** Credential loading follows this priority:
1. `adobe_credentials.json` file
2. `ADOBE_CLIENT_ID` / `ADOBE_CLIENT_SECRET` environment variables
3. Interactive prompt (saves to file for future use)

**Rule 6:** The `adobe_credentials.json` file MUST be in `.gitignore` and never committed.

## Related Standards

- Standard 001 (pikepdf for verification)
- Standard 004 (URL-encoded filename handling)

## References

- `adobe_autotag_api.py` — Adobe Cloud API client implementation
- `adobe_auto.py` — COM automation fallback
- [Adobe PDF Services API docs](https://developer.adobe.com/document-services/docs/apis/)
- [Adobe Developer Console](https://developer.adobe.com/console)
