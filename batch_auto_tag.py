#!/usr/bin/env python3
"""
Batch Auto-Tag PDFs using Adobe Acrobat Pro COM Automation

Opens each PDF in Adobe Acrobat Pro, runs Auto-Tag Document, saves the tagged version.
Works on Windows with Adobe Acrobat Pro (not Reader).
"""

import os
import sys
import time
import json
from pathlib import Path

try:
    import win32com.client
    import pythoncom
except ImportError:
    print("Error: pywin32 not installed. Run: pip install pywin32")
    sys.exit(1)

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input_pdfs"
OUTPUT_DIR = SCRIPT_DIR / "adobe_tagged"
REPORT_PATH = OUTPUT_DIR / "auto_tag_report.json"

# PDFs that need tagging (untagged PDFs from our pipeline)
PDFS_TO_TAG = [
    "2022 Faculty Development Week.pdf",
    "2023FacultyStaffDevelopmentWeekPost.pdf",
    "2024 New Faculty Workshop.pdf",
    "Archived_OSL Advisory Board Charter.pdf",
    "DEAB_Charter.pdf",
    "NMT ASR 2024 FINAL.pdf",
]

def init_com():
    """Initialize COM threading."""
    pythoncom.CoInitialize()

def cleanup_com():
    """Clean up COM threading."""
    pythoncom.CoUninitialize()

def open_acrobat():
    """Launch or connect to Adobe Acrobat Pro."""
    init_com()
    try:
        # Try to get existing Acrobat instance
        app = win32com.client.Dispatch("AcroExch.App")
        return app
    except:
        # Launch new instance
        app = win32com.client.Dispatch("AcroExch.App")
        app.Show()
        return app

def open_pdf(av_doc, pdf_path):
    """Open a PDF in Acrobat."""
    try:
        success = av_doc.Open(str(pdf_path), "")
        if not success:
            return None
        pd_doc = av_doc.GetPDDoc()
        return pd_doc
    except Exception as e:
        print(f"  ✗ Failed to open: {e}")
        return None

def run_auto_tag(pd_doc):
    """
    Run Adobe's Auto-Tag Document feature.
    Uses JavaScript API to trigger the accessibility auto-tag.
    """
    try:
        jso = pd_doc.GetJSObject()
        # Execute the Auto-Tag menu item
        # This is equivalent to Tools > Accessibility > Auto-Tag Document
        jso.runMenuItem("TouchUp_AutoTag")
        
        # Wait for auto-tag to complete (it can take time for large PDFs)
        # Poll until the command finishes
        time.sleep(5)  # Initial wait
        
        # Check if document is now tagged
        struct_tree = pd_doc.GetJSObject().thisDoc.structTreeRoot
        if struct_tree:
            return True
        else:
            # Try waiting longer
            time.sleep(10)
            struct_tree = pd_doc.GetJSObject().thisDoc.structTreeRoot
            return bool(struct_tree)
    except Exception as e:
        print(f"  ✗ Auto-tag failed: {e}")
        return False

def save_pdf(pd_doc, output_path):
    """Save the PDF to the specified path."""
    try:
        # PDDoc.Save flags: 1 = full save
        pd_doc.Save(1, str(output_path))
        return True
    except Exception as e:
        print(f"  ✗ Save failed: {e}")
        return False

def close_pdf(av_doc, pd_doc):
    """Close the PDF document."""
    try:
        pd_doc.Close()
        av_doc.Close(True)
    except:
        pass

def tag_single_pdf(pdf_path, output_path):
    """Process a single PDF: open, auto-tag, save."""
    app = None
    av_doc = None
    pd_doc = None
    
    result = {
        "filename": pdf_path.name,
        "success": False,
        "tagged": False,
        "errors": []
    }
    
    try:
        # Initialize COM for this thread
        init_com()
        
        # Open Acrobat
        app = open_acrobat()
        av_doc = win32com.client.Dispatch("AcroExch.AVDoc")
        
        # Open PDF
        print(f"  Opening {pdf_path.name}...")
        pd_doc = open_pdf(av_doc, pdf_path)
        if not pd_doc:
            result["errors"].append("Failed to open PDF")
            return result
        
        # Check if already tagged
        jso = pd_doc.GetJSObject()
        struct_tree = jso.thisDoc.structTreeRoot
        if struct_tree:
            print(f"  Already tagged, skipping...")
            result["tagged"] = True
            result["success"] = True
            # Still save to output
            if save_pdf(pd_doc, output_path):
                print(f"  ✓ Saved to {output_path.name}")
            return result
        
        # Run Auto-Tag
        print(f"  Running Auto-Tag Document...")
        tagged = run_auto_tag(pd_doc)
        
        if tagged:
            print(f"  ✓ Auto-Tag completed successfully")
            result["tagged"] = True
            
            # Save tagged PDF
            if save_pdf(pd_doc, output_path):
                print(f"  ✓ Saved tagged PDF to {output_path.name}")
                result["success"] = True
            else:
                result["errors"].append("Failed to save")
        else:
            result["errors"].append("Auto-Tag did not complete successfully")
            
    except Exception as e:
        result["errors"].append(str(e))
        print(f"  ✗ Error: {e}")
    finally:
        # Cleanup
        if av_doc and pd_doc:
            close_pdf(av_doc, pd_doc)
        cleanup_com()
    
    return result

def main():
    """Main entry point."""
    print("=" * 70)
    print("Batch Auto-Tag PDFs - Adobe Acrobat Pro Automation")
    print("=" * 70)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect PDFs to process
    pdfs_to_process = []
    for name in PDFS_TO_TAG:
        # Check input_pdfs first
        input_path = INPUT_DIR / name
        if input_path.exists():
            pdfs_to_process.append(input_path)
        else:
            # Check done/ and needs_review/
            for subdir in ["done", "needs_review", "adobe_fixed", "auto_fixed"]:
                alt_path = SCRIPT_DIR / subdir / name
                if alt_path.exists():
                    pdfs_to_process.append(alt_path)
                    break
    
    if not pdfs_to_process:
        print("No PDFs found to process.")
        return
    
    print(f"\nFound {len(pdfs_to_process)} PDF(s) to auto-tag:\n")
    for p in pdfs_to_process:
        print(f"  • {p.name}")
    
    print("\n" + "-" * 70)
    print("Starting batch auto-tag...\n")
    
    results = []
    for i, pdf_path in enumerate(pdfs_to_process, 1):
        print(f"[{i}/{len(pdfs_to_process)}] Processing: {pdf_path.name}")
        output_path = OUTPUT_DIR / pdf_path.name
        result = tag_single_pdf(pdf_path, output_path)
        results.append(result)
        print()
    
    # Generate report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "tagged": sum(1 for r in results if r["tagged"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print("\n" + "=" * 70)
    print("BATCH AUTO-TAG COMPLETE")
    print("=" * 70)
    print(f"  Total processed: {report['total']}")
    print(f"  ✓ Successfully tagged: {report['tagged']}")
    print(f"  ✗ Failed: {report['failed']}")
    print(f"\n  Tagged PDFs saved to: {OUTPUT_DIR}")
    print(f"  Report saved to: {REPORT_PATH}")

if __name__ == "__main__":
    main()
