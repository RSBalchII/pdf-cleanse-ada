# Standard 003: Adobe Auto-Tag — Cloud API Primary, COM Fallback

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** `adobe_autotag_api.py`, `adobe_auto.py`, `batch_auto_tag.py`, `server.js`

## Pain Point

Initial attempts to auto-tag PDFs using **Adobe Acrobat Pro COM automation** (`win32com.client`) encountered severe reliability issues:

1. **Async with no callback:** `jso.runMenuItem("TouchUp_AutoTag")` fires and returns immediately. There is no completion event or callback.
2. **No result extraction:** Adobe's COM API does not expose accessibility checker results programmatically.
3. **COM threading:** Python's COM automation requires `pythoncom.CoInitialize()` and `CoUninitialize()` per thread — easy to get wrong in batch processing.
4. **Silent crashes:** Acrobat crashes without error messages on complex PDFs (72+ pages, many images).
5. **Visibility requirement:** Acrobat must be visible and responsive during processing — cannot run headless.
6. **No progress indicator:** Cannot determine if auto-tag is 10% done or 90% done.

The polling workaround (`while not structTreeRoot: sleep(5)`) is unreliable and can hang indefinitely.

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
        │  3. POST /assets
        │     {mediaType: "application/pdf"}
        │  4. {assetID, uploadUri}
        ▼
┌───────────────┐                      ┌──────────────────┐
│               │  5. PUT uploadUri    │                  │
│  PDF bytes    │ ───────────────────► │  S3 Storage      │
│               │  6. 200 OK           │                  │
└───────┬───────┘                      └──────────────────┘
        │
        │  7. POST /operation/autotag
        │     {assetID, shiftHeadings, generateReport}
        │  8. 201 Location: /operation/autotag/{jobID}/status
        ▼
┌───────────────┐                      ┌──────────────────┐
│               │  9. GET .../status   │  Auto-Tag Engine │
│  Poll loop    │ ───────────────────► │  (ML model)      │
│  every 15s    │  10. {status:"done"} │                  │
└───────┬───────┘                      └──────────────────┘
        │
        │  11. GET /assets/{assetID}
        │  12. {downloadUri}
        ▼
┌───────────────┐                      ┌──────────────────┐
│               │  13. GET downloadUri │                  │
│  Save to      │ ───────────────────► │  S3 Storage      │
│  adobe_tagged/│  14. PDF bytes       │                  │
└───────────────┘                      └──────────────────┘
```

**COM automation** (`adobe_auto.py`, `batch_auto_tag.py`) remains as a fallback for offline environments.

## Definitive Standard

**Rule 1:** The **primary** auto-tag path is Adobe Cloud API (`adobe_autotag_api.py`). This is the default in the web UI.

**Rule 2:** COM automation (`adobe_auto.py`) is a **fallback** for environments without internet access or without Adobe API credentials.

**Rule 3:** The Adobe API client MUST implement:
- Token management with auto-refresh (check expiry, refresh at 60s before expiry)
- Session-based requests with persistent `x-api-key` and `Authorization: Bearer` headers
- Two-step upload: `POST /assets` → `PUT` to presigned URL
- Job polling with configurable timeout (default 600s) and interval (default 15s)
- Two-step download: `GET /assets/{id}` → `GET downloadUri`
- Post-download verification: verify `/StructTreeRoot` exists using pikepdf

**Rule 4:** Credential loading follows this priority:
1. `adobe_credentials.json` file
2. `ADOBE_CLIENT_ID` / `ADOBE_CLIENT_SECRET` environment variables
3. Interactive prompt (saves to file for future use)

**Rule 5:** The `adobe_credentials.json` file MUST be in `.gitignore` and never committed.

## Related Standards

- Standard 001 (pikepdf for verification)
- Standard 004 (URL-encoded filename handling)

## References

- `adobe_autotag_api.py` — Adobe Cloud API client implementation
- `adobe_auto.py` — COM automation fallback
- [Adobe PDF Services API docs](https://developer.adobe.com/document-services/docs/apis/)
- [Adobe Developer Console](https://developer.adobe.com/console)
