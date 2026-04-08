#!/usr/bin/env python3
"""
Batch Auto-Tag PDFs via Adobe Acrobat Pro COM Automation

Opens each PDF in Acrobat Pro, runs Auto-Tag Document, saves tagged version.
Requires Adobe Acrobat Pro (not Reader) installed on Windows.

Usage:
    python batch_auto_tag_acrobat.py
"""

import os
import sys
import time
import json
import codecs
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

try:
    import win32com.client
    import pythoncom
except ImportError:
    print("Error: pywin32 not installed. Run: pip install pywin32")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "needs_review"
OUTPUT_DIR = SCRIPT_DIR / "adobe_tagged"
REPORT_PATH = OUTPUT_DIR / "acrobat_auto_tag_report.json"

# PDFs that need tagging
PDFS_TO_TAG = [
    "2022 Faculty Development Week.pdf",
    "2023FacultyStaffDevelopmentWeekPost.pdf",
    "2024 Faculty Staff Development Week.pdf",
    "2024 New Faculty Workshop.pdf",
    "2025 Faculty Staff Development Week.pdf",
    "Archived_ACCREDITATION TASK FORCE SUBCOMMITTEE MEMBERSHIP.pdf",
    "Archived_OSL Advisory Board Charter.pdf",
    "Archived_TF_Charter.pdf",
    "Argos_advisor_rpt.pdf",
    "AssessmentFacultyDevelopmentWeek2019.pdf",
    "DEAB_Charter.pdf",
    "EvalofDistanceEducation_STA_2021.pdf",
    "Gen_ed_assessment_July_29_2019.pdf",
    "NMT 2025 CITI Training Guide.pdf",
    "NMT ASR 2024 FINAL.pdf",
    "Policy_on_Policy_APPROVED_12.7.18.pdf",
    "Published Draft of 2021 Faculty Development Week.pdf",
    "RevisedBloomsHandout-1_IOWA State.pdf",
    "revised_rubric.pdf",
]


def init_com():
    """Initialize COM threading."""
    pythoncom.CoInitialize()

def cleanup_com():
    """Clean up COM threading."""
    try:
        pythoncom.CoUninitialize()
    except:
        pass


def is_already_tagged(pdf_path):
    """Check if PDF already has a structure tree using pikepdf."""
    try:
        import pikepdf
        with pikepdf.open(pdf_path) as pdf:
            return pdf.Root.get("/StructTreeRoot") is not None
    except:
        return False


def auto_tag_single_pdf(pdf_path, output_path):
    """
    Process a single PDF: open in Acrobat, auto-tag, save.
    Returns dict with results.
    """
    result = {
        "filename": pdf_path.name,
        "input_path": str(pdf_path),
        "output_path": str(output_path),
        "success": False,
        "tagged": False,
        "already_tagged": False,
        "errors": [],
        "elapsed_seconds": 0,
    }

    start = time.time()

    try:
        init_com()

        # Check if already tagged
        if is_already_tagged(pdf_path):
            print(f"  Already tagged, skipping...")
            result["already_tagged"] = True
            result["tagged"] = True
            result["success"] = True
            # Copy to output anyway
            import shutil
            shutil.copy2(pdf_path, output_path)
            return result

        # Launch Acrobat Pro
        print(f"  Launching Acrobat Pro...")
        app = win32com.client.Dispatch("AcroExch.App")
        
        # Hide Acrobat window (optional - set to True to see it working)
        # app.Show()  # Uncomment to make Acrobat visible

        # Open the PDF
        av_doc = win32com.client.Dispatch("AcroExch.AVDoc")
        print(f"  Opening {pdf_path.name}...")
        
        if not av_doc.Open(str(pdf_path), ""):
            result["errors"].append("Failed to open PDF in Acrobat")
            return result

        pd_doc = av_doc.GetPDDoc()

        # Get JSObject for advanced operations
        jso = pd_doc.GetJSObject()

        # Run Auto-Tag Document using app.execMenuItem (more reliable than jso.runMenuItem)
        print(f"  Running Auto-Tag Document...")
        
        # Make sure the document is active
        av_doc.BringToFront()
        
        # Use app.execMenuItem instead of jso.runMenuItem
        try:
            app.execMenuItem("TouchUp_AutoTag")
        except:
            # Fallback to JSObject method
            jso.runMenuItem("TouchUp_AutoTag")

        # Wait for auto-tag to complete
        # Auto-tag can take time depending on PDF size
        pages = pd_doc.GetNumPages()
        wait_time = max(10, min(60, pages * 2))  # 2 seconds per page, min 10s, max 60s
        print(f"  Waiting {wait_time}s for auto-tag ({pages} pages)...")
        time.sleep(wait_time)

        # Check if document is now tagged
        struct_tree = jso.thisDoc.structTreeRoot
        if struct_tree:
            print(f"  Auto-Tag completed successfully!")
            result["tagged"] = True

            # Save the tagged PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if pd_doc.Save(1, str(output_path)):  # 1 = full save
                print(f"  Saved to {output_path.name}")
                result["success"] = True
            else:
                result["errors"].append("Failed to save tagged PDF")
        else:
            # Wait longer and check again
            print(f"  Structure tree not found, waiting more...")
            time.sleep(30)
            struct_tree = jso.thisDoc.structTreeRoot
            if struct_tree:
                print(f"  Auto-Tag completed (after extended wait)!")
                result["tagged"] = True
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if pd_doc.Save(1, str(output_path)):
                    print(f"  Saved to {output_path.name}")
                    result["success"] = True
            else:
                result["errors"].append("Auto-Tag did not produce a structure tree")

        # Close PDF
        pd_doc.Close()
        av_doc.Close(True)

    except Exception as e:
        result["errors"].append(str(e))
        print(f"  Error: {e}")
    finally:
        cleanup_com()

    result["elapsed_seconds"] = round(time.time() - start, 1)
    return result


def main():
    """Main entry point."""
    print("=" * 70)
    print("Batch Auto-Tag PDFs — Adobe Acrobat Pro COM Automation")
    print("=" * 70)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Find PDFs to process
    pdfs_to_process = []
    for name in PDFS_TO_TAG:
        # Check multiple possible locations
        for search_dir in [SCRIPT_DIR / "input_pdfs", SCRIPT_DIR / "needs_review", 
                          SCRIPT_DIR / "done", SCRIPT_DIR / "adobe_tagged"]:
            pdf_path = search_dir / name
            if pdf_path.exists():
                pdfs_to_process.append(pdf_path)
                break

    if not pdfs_to_process:
        print("No PDFs found to process.")
        return

    print(f"Found {len(pdfs_to_process)} PDF(s) to auto-tag:\n")
    for p in pdfs_to_process:
        size = p.stat().st_size / 1024
        print(f"  - {p.name} ({size:.1f} KB)")

    print(f"\nEstimated: ~1-2 minutes per PDF (depends on page count)")
    
    # Auto-confirm if running non-interactively or if 'y' is passed
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        confirm = 'y'
        print(f"\nAuto-confirming: Processing {len(pdfs_to_process)} PDF(s)...")
    else:
        confirm = input(f"\nProcess {len(pdfs_to_process)} PDF(s)? (y/n): ").strip().lower()
    
    if confirm != "y":
        print("Aborted.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process each PDF
    results = []
    for i, pdf_path in enumerate(pdfs_to_process, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(pdfs_to_process)}] Processing: {pdf_path.name}")
        print(f"{'='*60}")

        output_path = OUTPUT_DIR / pdf_path.name
        result = auto_tag_single_pdf(pdf_path, output_path)
        results.append(result)

        if result["success"]:
            print(f"  ✅ COMPLETE ({result['elapsed_seconds']}s)")
        elif result["already_tagged"]:
            print(f"  ⏭️  Already tagged, skipped")
        else:
            print(f"  ❌ FAILED ({result['elapsed_seconds']}s)")
            for err in result["errors"]:
                print(f"     Error: {err}")

    # Summary
    total = len(results)
    successful = sum(1 for r in results if r["success"] and not r["already_tagged"])
    skipped = sum(1 for r in results if r["already_tagged"])
    failed = sum(1 for r in results if not r["success"])
    total_time = sum(r["elapsed_seconds"] for r in results)

    print(f"\n{'='*70}")
    print("BATCH AUTO-TAG COMPLETE")
    print(f"{'='*70}")
    print(f"  Total processed: {total}")
    print(f"  ✅ Newly tagged: {successful}")
    print(f"  ⏭️  Already tagged: {skipped}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏱️  Total time: {total_time:.1f}s")
    print(f"\n  Tagged PDFs saved to: {OUTPUT_DIR}")

    # Save report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "successful": successful,
        "skipped": skipped,
        "failed": failed,
        "total_time_seconds": total_time,
        "results": results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
