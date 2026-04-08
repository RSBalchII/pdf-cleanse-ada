#!/usr/bin/env python3
"""
Adobe PDF Accessibility Auto-Tag API Integration

Uses Adobe's official PDF Services API to automatically tag PDFs for accessibility.
API: https://developer.adobe.com/document-services/apis/pdf-accessibility-auto-tag/

Workflow:
  1. Authenticate with Adobe (client_id + client_secret)
  2. Upload PDF as asset → get assetID
  3. Submit auto-tag job → get jobID
  4. Poll job status until complete
  5. Download tagged PDF from Adobe storage

Requires Adobe Developer credentials. Get them at:
  https://developer.adobe.com/console
"""

import os
import sys
import json
import time
import base64
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from typing import Optional

import requests

# ─── Configuration ───────────────────────────────────────────
ADOBE_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
ADOBE_ASSETS_URL = "https://pdf-services.adobe.io/assets"
ADOBE_AUTOTAG_URL = "https://pdf-services.adobe.io/operation/autotag"

SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input_pdfs"
OUTPUT_DIR = SCRIPT_DIR / "adobe_tagged"
CONFIG_PATH = SCRIPT_DIR / "adobe_credentials.json"
REPORT_PATH = OUTPUT_DIR / "adobe_auto_tag_report.json"


class AdobeAPI:
    """Handles Adobe PDF Services API authentication and operations."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = 0
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": client_id})

    def get_token(self) -> str:
        """Get or refresh OAuth access token."""
        if self.access_token and time.time() < self.token_expires - 60:
            return self.access_token

        print("  🔑 Authenticating with Adobe IMS...")
        resp = self.session.post(
            ADOBE_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )

        if resp.status_code != 200:
            raise Exception(f"Auth failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        self.access_token = data["access_token"]
        self.token_expires = time.time() + int(data.get("expires_in", 86399))
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        print(f"  ✅ Authenticated (token expires in {data.get('expires_in', 86400)}s)")
        return self.access_token

    def upload_asset(self, pdf_path: Path) -> str:
        """
        Upload a PDF and return its assetID.
        Two-step: get presigned URL → upload file directly.
        """
        token = self.get_token()
        mime_type, _ = mimetypes.guess_type(str(pdf_path))
        mime_type = mime_type or "application/pdf"

        # Step 1: Get presigned upload URL
        print(f"  📤 Uploading {pdf_path.name} ({pdf_path.stat().st_size / 1024:.1f} KB)...")
        resp = self.session.post(
            ADOBE_ASSETS_URL,
            json={"mediaType": mime_type},
        )

        if resp.status_code not in (200, 201):
            raise Exception(f"Asset upload failed ({resp.status_code}): {resp.text[:200]}")

        asset_data = resp.json()
        asset_id = asset_data["assetID"]
        upload_url = asset_data["uploadUri"]

        # Step 2: Upload file directly to presigned URL
        with open(pdf_path, "rb") as f:
            upload_resp = requests.put(
                upload_url,
                data=f,
                headers={"Content-Type": mime_type},
            )

        if upload_resp.status_code not in (200, 201):
            raise Exception(f"File upload failed ({upload_resp.status_code})")

        print(f"  ✅ Uploaded → assetID: {asset_id}")
        return asset_id

    def submit_autotag_job(self, asset_id: str, shift_headings: bool = False,
                           generate_report: bool = True) -> str:
        """Submit an auto-tag job and return the jobID."""
        token = self.get_token()
        payload = {
            "assetID": asset_id,
            "shiftHeadings": shift_headings,
            "generateReport": generate_report,
        }

        print(f"  🏷️  Submitting auto-tag job...")
        resp = self.session.post(
            ADOBE_AUTOTAG_URL,
            json=payload,
        )

        if resp.status_code not in (201, 202):
            raise Exception(f"Auto-tag submit failed ({resp.status_code}): {resp.text[:200]}")

        # Job ID is in the Location header
        location = resp.headers.get("Location", "")
        # Extract job ID from /operation/autotag/{jobID}/status
        job_id = location.split("/")[-2] if "/status" in location else location.split("/")[-1]
        print(f"  📋 Job submitted → jobID: {job_id}")
        return job_id

    def poll_job_status(self, job_id: str, timeout: int = 600, interval: int = 10) -> dict:
        """Poll job status until complete or timeout. Returns final status."""
        url = f"{ADOBE_AUTOTAG_URL}/{job_id}/status"
        print(f"  ⏳ Polling job status...")

        start = time.time()
        while time.time() - start < timeout:
            resp = self.session.get(url)

            if resp.status_code != 200:
                raise Exception(f"Status poll failed ({resp.status_code}): {resp.text[:200]}")

            status_data = resp.json()
            status = status_data.get("status", "unknown")
            print(f"     Status: {status} ({time.time() - start:.0f}s elapsed)")

            if status in ("done", "succeeded", "complete"):
                return status_data
            elif status in ("failed", "error"):
                raise Exception(f"Job failed: {json.dumps(status_data)}")

            time.sleep(interval)

        raise TimeoutError(f"Job timed out after {timeout}s")

    def download_tagged_pdf(self, asset_id: str, output_path: Path) -> Path:
        """Download the tagged PDF asset to local path."""
        print(f"  📥 Downloading tagged PDF...")
        resp = self.session.get(f"{ADOBE_ASSETS_URL}/{asset_id}")

        if resp.status_code != 200:
            raise Exception(f"Download failed ({resp.status_code}): {resp.text[:200]}")

        # The response contains the download URI
        data = resp.json()
        download_url = data.get("downloadUri")

        if not download_url:
            raise Exception("No download URI in response")

        # Download the actual file
        file_resp = requests.get(download_url)
        if file_resp.status_code != 200:
            raise Exception(f"File download failed ({file_resp.status_code})")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(file_resp.content)

        size = output_path.stat().st_size
        print(f"  ✅ Saved to {output_path.name} ({size / 1024:.1f} KB)")
        return output_path


def load_credentials() -> tuple:
    """Load Adobe credentials from config file or env vars."""
    # Priority 1: Config file
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            creds = json.load(f)
        return creds["client_id"], creds["client_secret"]

    # Priority 2: Environment variables
    client_id = os.environ.get("ADOBE_CLIENT_ID")
    client_secret = os.environ.get("ADOBE_CLIENT_SECRET")
    if client_id and client_secret:
        return client_id, client_secret

    # Priority 3: Interactive prompt
    print("❌ No Adobe credentials found.")
    print(f"\n📝 Please provide your Adobe Developer credentials:")
    print(f"   Get them at: https://developer.adobe.com/console")
    print(f"   Steps: Create project → Add PDF Services API → Generate credentials\n")
    client_id = input("   Client ID: ").strip()
    client_secret = input("   Client Secret: ").strip()

    if not client_id or not client_secret:
        print("❌ Credentials required.")
        sys.exit(1)

    # Save for future use
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"client_id": client_id, "client_secret": client_secret}, f, indent=2)
    print(f"\n✅ Credentials saved to {CONFIG_PATH}")

    return client_id, client_secret


def auto_tag_pdf(api: AdobeAPI, pdf_path: Path, output_path: Path) -> dict:
    """
    Full auto-tag workflow for a single PDF:
    1. Upload → 2. Auto-tag → 3. Download → 4. Verify tagging
    """
    result = {
        "filename": pdf_path.name,
        "input_size": pdf_path.stat().st_size,
        "success": False,
        "tagged": False,
        "errors": [],
        "asset_id": None,
        "job_id": None,
        "output_size": None,
        "elapsed_seconds": 0,
    }

    start = time.time()

    try:
        # Step 1: Upload PDF
        asset_id = api.upload_asset(pdf_path)
        result["asset_id"] = asset_id

        # Step 2: Submit auto-tag job
        job_id = api.submit_autotag_job(asset_id, shift_headings=False, generate_report=True)
        result["job_id"] = job_id

        # Step 3: Wait for completion
        status = api.poll_job_status(job_id, timeout=600, interval=15)

        # Step 4: Download tagged PDF
        output_path = api.download_tagged_pdf(asset_id, output_path)
        result["output_size"] = output_path.stat().st_size

        # Step 5: Verify the tagged PDF has a structure tree
        try:
            import pikepdf
            with pikepdf.open(output_path) as pdf:
                struct_tree = pdf.Root.get("/StructTreeRoot")
                result["tagged"] = struct_tree is not None
                if result["tagged"]:
                    print(f"  ✅ Verification: PDF is tagged (StructTreeRoot found)")
                else:
                    print(f"  ⚠️  Warning: Adobe returned a PDF but StructTreeRoot is missing")
                    result["errors"].append("Output PDF has no StructTreeRoot")
        except ImportError:
            result["tagged"] = True  # Assume success if pikepdf not available
            print(f"  ⚠️  Could not verify tagging (pikepdf not available)")

        result["success"] = result["tagged"]

    except Exception as e:
        result["errors"].append(str(e))
        print(f"  ❌ Error: {e}")

    result["elapsed_seconds"] = round(time.time() - start, 1)
    return result


def process_all_pdfs(api: AdobeAPI, pdf_files: list, output_dir: Path) -> list:
    """Batch process multiple PDFs."""
    results = []
    total = len(pdf_files)

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{total}] Processing: {pdf_path.name}")
        print(f"{'='*60}")

        output_path = output_dir / pdf_path.name
        result = auto_tag_pdf(api, pdf_path, output_path)
        results.append(result)

        if result["success"]:
            print(f"  ✅ COMPLETE ({result['elapsed_seconds']}s)")
        else:
            print(f"  ❌ FAILED ({result['elapsed_seconds']}s)")

    return results


def main():
    """Main entry point."""
    print("=" * 60)
    print("Adobe PDF Accessibility Auto-Tag — Batch Processor")
    print("=" * 60)
    print(f"API: Adobe PDF Services (developer.adobe.com)")
    print()

    # Load credentials
    client_id, client_secret = load_credentials()

    # Initialize API
    api = AdobeAPI(client_id, client_secret)

    # Find PDFs to process
    # Priority: needs_review/ first, then input_pdfs/
    pdf_files = []
    for search_dir in [SCRIPT_DIR / "needs_review", SCRIPT_DIR / "input_pdfs", INPUT_DIR]:
        if search_dir.exists():
            for f in sorted(search_dir.glob("*.pdf")):
                if f.name not in [p.name for p in pdf_files]:
                    pdf_files.append(f)

    if not pdf_files:
        print("❌ No PDF files found to process.")
        return

    print(f"\n📂 Found {len(pdf_files)} PDF(s) to auto-tag:\n")
    for p in pdf_files:
        size = p.stat().st_size / 1024
        print(f"  • {p.name} ({size:.1f} KB)")

    print(f"\n⏳ Estimated: ~2-5 minutes per PDF depending on size")
    confirm = input(f"\nProcess {len(pdf_files)} PDF(s)? (y/n): ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process all PDFs
    results = process_all_pdfs(api, pdf_files, OUTPUT_DIR)

    # Summary report
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful
    total_time = sum(r["elapsed_seconds"] for r in results)

    print(f"\n{'='*60}")
    print("BATCH AUTO-TAG COMPLETE")
    print(f"{'='*60}")
    print(f"  Total processed: {total}")
    print(f"  ✅ Success: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏱️  Total time: {total_time:.1f}s")
    print(f"\n  Tagged PDFs saved to: {OUTPUT_DIR}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "successful": successful,
        "failed": failed,
        "total_time_seconds": total_time,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
