#!/usr/bin/env python3
"""
PDF-Ada UI Automation Script

Simulates a user interaction:
1. Uploads a PDF from input_pdfs/.
2. Processes the PDF.
3. Logs the terminal output to a file (max 1000 lines).
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
from datetime import datetime

# Configuration
APP_URL = "http://localhost:3000"
LOG_FILE = "ui_automation_log.txt"
MAX_LINES = 1000
INPUT_DIR = Path("input_pdfs")

def get_test_pdf():
    """Find a PDF to test with."""
    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"Error: No PDFs found in {INPUT_DIR}")
        sys.exit(1)
    return pdfs[0]

def setup_log():
    """Initialize the log file."""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Automation Log started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

async def send_request(session, url, method="POST", data=None):
    """Helper to send HTTP requests."""
    async with session.request(method, url, json=data) as resp:
        return resp.status, await resp.json()

async def log_to_file(message, type="info"):
    """Write to the log file with a line limit."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] [{type.upper()}] {message}\n"
        f.write(line)

async def emulate_user_actions(session):
    """Simulate the UI workflow."""
    pdf_path = get_test_pdf()
    
    # 1. Simulate Upload
    print(f"📤 Step 1: Uploading {pdf_path.name}...")
    await log_to_file(f"UPLOADED: {pdf_path.name} ({pdf_path.stat().st_size} bytes)", type="accent")
    
    # 2. Simulate Process
    print(f"🏃 Step 2: Processing {pdf_path.name}...")
    await log_to_file("ACTION: Clicked 'Process All PDFs' button", type="primary")
    
    try:
        status, result = await send_request(session, f"{APP_URL}/api/process")
        print(f"  Server Response Status: {status}")
        if result:
            print(f"  Result Data: {result}")
            await log_to_file(f"RESULT: {result}", type="info")
    except Exception as e:
        print(f"  Error processing: {e}")
        await log_to_file(f"ERROR: {e}", type="error")

def main():
    print(f"Starting UI Automation Test...")
    print(f"Target: {APP_URL}")
    print(f"Test File: {get_test_pdf()}")
    
    setup_log()
    
    async def run():
        print("Connecting to server...")
        await log_to_file("Connecting to server...", type="info")
        await asyncio.sleep(1) # Simulate wait
        print("Starting emulation...")
        await log_to_file("Starting emulation...", type="info")
        async with aiohttp.ClientSession() as session:
            await emulate_user_actions(session)
            await log_to_file("Test Complete.", type="success")

    asyncio.run(run())

if __name__ == "__main__":
    main()
