#!/usr/bin/env python3
"""
ADA Compliance Preprocessor for University Policy PDFs

This script processes PDFs for ADA compliance by:
1. Injecting official /Title metadata from filename
2. Setting /Lang to EN-US for screen reader compatibility
3. Analyzing tag structure (/MarkInfo -> /Marked)
4. Counting XObject images for triage prioritization
5. Generating a CSV triage report

Uses pikepdf to preserve existing structural /StructTreeRoot and /MarkInfo tags.
"""

import csv
import os
from pathlib import Path

import pikepdf
from pikepdf import Name, Dictionary, Array


# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input_pdfs"
OUTPUT_DIR = SCRIPT_DIR / "staged_compliance"
REPORT_PATH = SCRIPT_DIR / "triage_report.csv"

# ADA compliance metadata
LANG_CODE = "en-US"


def count_xobject_images(pdf: pikepdf.Pdf) -> int:
    """
    Count all XObject images in the PDF document.
    Traverses all pages and their resources to find Image XObjects.
    """
    image_count = 0
    
    for page in pdf.pages:
        resources = page.get("/Resources", Dictionary())
        xobjects = resources.get("/XObject", Dictionary())
        
        if xobjects is None:
            continue
            
        for key, xobj in xobjects.items():
            if xobj is None:
                continue
            # Check if this XObject is an image
            xobj_type = xobj.get("/Subtype")
            if xobj_type == Name("/Image"):
                image_count += 1
    
    return image_count


def check_is_tagged(pdf: pikepdf.Pdf) -> bool:
    """
    Check if the PDF has basic tag structure.
    Looks for /MarkInfo -> /Marked set to true.
    """
    try:
        catalog = pdf.Root
        mark_info = catalog.get("/MarkInfo")
        
        if mark_info is None:
            return False
        
        marked = mark_info.get("/Marked")
        return marked is True or marked == Name("/true")
    except Exception:
        return False


def inject_metadata(pdf: pikepdf.Pdf, title: str) -> None:
    """
    Inject ADA-compliant metadata into the PDF.
    - Sets /Title to the provided title string
    - Sets /Lang to en-US for screen reader compatibility
    
    This modifies the document catalog in-place.
    """
    # Ensure metadata dictionary exists
    if "/Metadata" not in pdf.Root:
        pdf.Root.Metadata = Dictionary()
    
    # Inject Title metadata
    pdf.Root.Title = title
    
    # Inject Lang for screen reader compliance
    pdf.Root.Lang = LANG_CODE


def process_pdf(input_path: Path, output_path: Path) -> dict:
    """
    Process a single PDF file for ADA compliance.
    
    Args:
        input_path: Path to the input PDF file
        output_path: Path where the processed PDF will be saved
        
    Returns:
        Dictionary with processing results for the triage report
    """
    filename = input_path.stem  # Filename without .pdf extension
    
    with pikepdf.open(input_path) as pdf:
        # Inject metadata
        inject_metadata(pdf, filename)
        
        # Analyze structure before saving
        is_tagged = check_is_tagged(pdf)
        image_count = count_xobject_images(pdf)
        
        # Save with preserved structure
        # pikepdf preserves existing /StructTreeRoot and /MarkInfo by default
        pdf.save(output_path, preserve_pdfa=True)
    
    return {
        "Filename": filename,
        "Title_Injected": filename,
        "Lang_Injected": LANG_CODE,
        "Is_Tagged": is_tagged,
        "Image_Count": image_count
    }


def generate_triage_report(results: list[dict]) -> None:
    """
    Generate CSV triage report with processing results.
    
    The report helps identify files requiring manual intervention:
    - Is_Tagged = False: Needs structural tagging
    - High Image_Count: May need alt-text review
    """
    fieldnames = ["Filename", "Title_Injected", "Lang_Injected", "Is_Tagged", "Image_Count"]
    
    with open(REPORT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Triage report saved to: {REPORT_PATH}")


def main():
    """
    Main entry point for the ADA compliance preprocessor.
    """
    print("=" * 60)
    print("ADA Compliance PDF Preprocessor")
    print("=" * 60)
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files in input directory
    if not INPUT_DIR.exists():
        print(f"Error: Input directory not found: {INPUT_DIR}")
        print("Please create the 'input_pdfs' directory and add PDF files to process.")
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
        
        output_path = OUTPUT_DIR / pdf_path.name
        
        try:
            result = process_pdf(pdf_path, output_path)
            results.append(result)
            
            status_tagged = "✓ Tagged" if result["Is_Tagged"] else "✗ Untagged"
            print(f"  -> {status_tagged}, Images: {result['Image_Count']}")
            
        except Exception as e:
            print(f"  -> ERROR: {e}")
            results.append({
                "Filename": pdf_path.stem,
                "Title_Injected": pdf_path.stem,
                "Lang_Injected": LANG_CODE,
                "Is_Tagged": False,
                "Image_Count": -1
            })
    
    # Generate triage report
    print()
    generate_triage_report(results)
    
    # Summary
    print("\n" + "=" * 60)
    print("Processing Complete")
    print("=" * 60)
    
    untagged_count = sum(1 for r in results if not r["Is_Tagged"])
    high_image_count = sum(1 for r in results if r["Image_Count"] > 5)
    
    print(f"Total processed: {len(results)}")
    print(f"Untagged PDFs (need manual tagging): {untagged_count}")
    print(f"High image count PDFs (>5 images): {high_image_count}")
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Review triage_report.csv for manual intervention priorities")


if __name__ == "__main__":
    main()
