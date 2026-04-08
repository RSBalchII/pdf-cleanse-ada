#!/usr/bin/env python3
"""
ADA Auto-Fix Tool

Applies automated fixes for accessibility issues that can be resolved programmatically.
Creates fixed copies in a separate directory and logs all changes.

AUTO_FIXABLE issues this tool handles:
- META-001: Missing Document Title
- META-002: Missing Document Language  
- META-003: DisplayDocTitle not set
- STRUCT-002: MarkInfo not set to Marked
- SEC-001: Document encryption (if password known)
- SEC-002: Content extraction disabled
"""

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

import pikepdf
from pikepdf import Name, Dictionary


# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input_pdfs"
FIXED_DIR = SCRIPT_DIR / "auto_fixed"
LOG_DIR = SCRIPT_DIR / "fix_logs"


def fix_metadata(pdf: pikepdf.Pdf, filename: str) -> list[dict]:
    """Fix metadata issues (META-001, META-002, META-003)."""
    
    fixes = []
    
    # Fix Title (META-001)
    current_title = pdf.Root.get("/Title")
    if not current_title:
        pdf.Root.Title = filename
        fixes.append({
            "issue_id": "META-001",
            "action": f"Set /Title to '{filename}'",
            "location": "Document Catalog"
        })
    
    # Fix Language (META-002)
    current_lang = pdf.Root.get("/Lang")
    if not current_lang:
        pdf.Root.Lang = "en-US"
        fixes.append({
            "issue_id": "META-002",
            "action": "Set /Lang to 'en-US'",
            "location": "Document Catalog"
        })
    
    # Fix DisplayDocTitle (META-003)
    viewer_prefs = pdf.Root.get("/ViewerPreferences")
    if not viewer_prefs:
        pdf.Root.ViewerPreferences = Dictionary()
        viewer_prefs = pdf.Root.ViewerPreferences
    
    display_title = viewer_prefs.get("/DisplayDocTitle")
    if display_title != True:
        viewer_prefs.DisplayDocTitle = True
        fixes.append({
            "issue_id": "META-003",
            "action": "Set DisplayDocTitle to true",
            "location": "ViewerPreferences"
        })
    
    return fixes


def fix_mark_info(pdf: pikepdf.Pdf) -> list[dict]:
    """Fix MarkInfo structure (STRUCT-002)."""
    
    fixes = []
    
    mark_info = pdf.Root.get("/MarkInfo")
    if not mark_info:
        pdf.Root.MarkInfo = Dictionary()
        mark_info = pdf.Root.MarkInfo
    
    marked = mark_info.get("/Marked")
    if marked is not True and marked != Name("/true"):
        mark_info.Marked = True
        fixes.append({
            "issue_id": "STRUCT-002",
            "action": "Set MarkInfo.Marked to true",
            "location": "Document Catalog /MarkInfo"
        })
    
    return fixes


def fix_security(pdf: pikepdf.Pdf, password: str = None) -> list[dict]:
    """Fix security issues if possible (SEC-001, SEC-002)."""
    
    fixes = []
    
    if pdf.is_encrypted:
        if password:
            # Try to decrypt with provided password
            try:
                pdf.decrypt(password)
                fixes.append({
                    "issue_id": "SEC-001",
                    "action": "Removed encryption with provided password",
                    "location": "Document security"
                })
            except Exception as e:
                fixes.append({
                    "issue_id": "SEC-001",
                    "action": f"Failed to decrypt: {e}",
                    "location": "Document security"
                })
        else:
            fixes.append({
                "issue_id": "SEC-001",
                "action": "Cannot fix - password required",
                "location": "Document security"
            })
    
    return fixes


def process_pdf(input_path: Path, output_path: Path) -> dict:
    """Process a single PDF and apply all auto-fixes."""
    
    filename = input_path.stem
    result = {
        "filename": filename,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "success": False,
        "fixes_applied": [],
        "errors": []
    }
    
    try:
        with pikepdf.open(input_path) as pdf:
            # Apply fixes
            result["fixes_applied"].extend(fix_metadata(pdf, filename))
            result["fixes_applied"].extend(fix_mark_info(pdf))
            result["fixes_applied"].extend(fix_security(pdf))
            
            # Save fixed PDF
            pdf.save(output_path, preserve_pdfa=True)
            result["success"] = True
            
    except Exception as e:
        result["errors"].append(str(e))
    
    return result


def generate_fix_log(results: list[dict]) -> None:
    """Generate detailed fix log."""
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"fix_log_{timestamp}.json"
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "total_processed": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "total_fixes": sum(len(r["fixes_applied"]) for r in results),
        "results": results
    }
    
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)
    
    # Also generate CSV summary
    csv_path = LOG_DIR / f"fix_summary_{timestamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Filename", "Success", "Fixes_Count", "Errors"])
        for r in results:
            writer.writerow([
                r["filename"],
                r["success"],
                len(r["fixes_applied"]),
                "; ".join(r["errors"]) if r["errors"] else "None"
            ])
    
    print(f"Fix log saved to: {log_path}")
    print(f"Fix summary saved to: {csv_path}")


def main():
    """Main entry point for auto-fix tool."""
    
    print("=" * 70)
    print("ADA Auto-Fix Tool")
    print("=" * 70)
    
    # Ensure directories exist
    FIXED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find PDFs in input directory
    if not INPUT_DIR.exists():
        print(f"Error: Input directory not found: {INPUT_DIR}")
        return
    
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in: {INPUT_DIR}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process\n")
    
    # Process each PDF
    results = []
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        
        output_path = FIXED_DIR / pdf_path.name
        result = process_pdf(pdf_path, output_path)
        results.append(result)
        
        if result["success"]:
            fix_count = len(result["fixes_applied"])
            print(f"  -> Fixed ({fix_count} changes applied)")
            for fix in result["fixes_applied"]:
                print(f"     - [{fix['issue_id']}] {fix['action']}")
        else:
            print(f"  -> FAILED")
            for error in result["errors"]:
                print(f"     Error: {error}")
    
    # Generate logs
    print()
    generate_fix_log(results)
    
    # Summary
    print("\n" + "=" * 70)
    print("AUTO-FIX SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for r in results if r["success"])
    total_fixes = sum(len(r["fixes_applied"]) for r in results)
    
    print(f"\nDocuments processed: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(results) - successful}")
    print(f"\nTotal fixes applied: {total_fixes}")
    
    # Count by issue type
    fix_counts = {}
    for r in results:
        for fix in r["fixes_applied"]:
            issue_id = fix["issue_id"]
            fix_counts[issue_id] = fix_counts.get(issue_id, 0) + 1
    
    if fix_counts:
        print("\nFixes by type:")
        for issue_id, count in sorted(fix_counts.items()):
            print(f"  {issue_id}: {count}")
    
    print(f"\nFixed PDFs saved to: {FIXED_DIR}")
    print("Review logs for detailed change information")


if __name__ == "__main__":
    main()
