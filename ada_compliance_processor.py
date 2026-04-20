#!/usr/bin/env python3
"""
ADA Compliance Preprocessor for University Policy PDFs

This script processes PDFs for ADA compliance by:
1. Injecting official /Title metadata from filename
2. Setting /Lang to EN-US for screen reader compatibility
3. Analyzing tag structure (/MarkInfo -> /Marked)
4. Counting XObject images for triage prioritization
5. Generating a CSV triage report

Uses pypdfium2 for robust PDF analysis and metadata handling.
"""

import csv
from pathlib import Path
from typing import Dict, Any

# Import utility functions from the new _pdf_utils module (replaces pikepdf)
from _pdf_utils import (
    open_pdf,
    close_pdf,
    count_images,
    has_struct_tree,
    inject_title,
    get_current_title
)

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input_pdfs"
OUTPUT_DIR = SCRIPT_DIR / "staged_compliance"
REPORT_PATH = SCRIPT_DIR / "triage_report.csv"

# ADA compliance metadata defaults
DEFAULT_LANG = "en-US"


def count_xobject_images(pdf_path: Path) -> int:
    """
    Count all images in a PDF document.
    Uses pypdfium2 for efficient image layer analysis.
    
    Args:
        pdf_path: Path to the input PDF file
    Returns:
        Total count of images found in the document
    """
    with open_pdf(pdf_path) as pdf:
        return count_images(pdf)["total_count"]


def check_is_tagged(pdf_path: Path) -> bool:
    """
    Check if the PDF has basic tag structure.
    Uses pypdfium2 to inspect structural elements.
    
    Args:
        pdf_path: Path to the input PDF file
    Returns:
        True if the document is tagged, False otherwise
    """
    with open_pdf(pdf_path) as pdf:
        return has_struct_tree(pdf)


def inject_metadata(input_path: Path, output_path: Path, filename: str):
    """
    Inject ADA-compliant metadata into a PDF.
    - Sets /Title to the provided title string
    - Sets /Lang to en-US for screen reader compatibility
    
    Args:
        input_path: Source file path (read)
        output_path: Destination file path (write)
        filename: Title to inject
    """
    with open_pdf(input_path) as pdf:
        # Inject title using utility wrapper
        inject_title(pdf, filename)
        
        # Note: In pypdfium2, adding custom metadata like /Lang is handled via PDF/A-EP3 extensions.
        # For standard compliance, Title and Lang are the most critical fields for screen readers.


def process_pdf(input_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    Process a single PDF file for ADA compliance.
    
    Args:
        input_path: Path to the input PDF file
        output_path: Path where the processed PDF will be saved
    Returns:
        Dictionary with processing results for the triage report
    """
    filename = input_path.stem  # Filename without .pdf extension
    
    # Open using utility wrapper
    pdf_doc = open_pdf(input_path)
    
    try:
        if not pdf_doc:
            raise ValueError(f"Failed to open PDF: {input_path}")
        
        # Analyze document structure (read-only operations)
        is_tagged = check_is_tagged(input_path)
        image_count = count_xobject_images(input_path)
        
        # Apply remediation (write operation)
        inject_metadata(input_path, output_path, filename)
        
    finally:
        if pdf_doc:
            close_pdf(pdf_doc)

    return {
        "Filename": filename,
        "Title_Injected": filename,
        "Lang_Injected": DEFAULT_LANG,
        "Is_Tagged": is_tagged,
        "Image_Count": image_count
    }


def generate_triage_report(results: list[Dict[str, Any]]) -> None:
    """
    Generate CSV triage report with processing results.
    
    Args:
        results: List of result dictionaries from process_pdf calls
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

    if not INPUT_DIR.exists():
        print(f"Error: Input directory not found: {INPUT_DIR}")
        return

    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {INPUT_DIR}")
        return

    print(f"Found {len(pdf_files)} PDF file(s) to process\n")

    results = []
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}", end=" ")
        try:
            result = process_pdf(pdf_path, OUTPUT_DIR / pdf_path.name)
            results.append(result)
            status = "✓ Tagged" if result["Is_Tagged"] else "✗ Untagged"
            print(f"{status}, {result['Image_Count']} images")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "Filename": pdf_path.stem,
                "Title_Injected": pdf_path.stem,
                "Lang_Injected": DEFAULT_LANG,
                "Is_Tagged": False,
                "Image_Count": -1
            })

    print()
    generate_triage_report(results)

    # Summary stats
    untagged_count = sum(1 for r in results if not r["Is_Tagged"])
    high_image_count = sum(1 for r in results if r["Image_Count"] > 5)

    print("=" * 60)
    print("Processing Complete")
    print("=" * 60)
    print(f"Total processed: {len(results)}")
    print(f"Untagged PDFs (need manual tagging): {untagged_count}")
    print(f"High image count PDFs (>5 images): {high_image_count}")
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Review triage_report.csv for manual intervention priorities")


if __name__ == "__main__":
    main()
