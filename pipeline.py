#!/usr/bin/env python3
"""
Enhanced PDF ADA Compliance Pipeline (Option A: Local Extraction)

Orchestrates the full workflow:
1. ASSESS — initial Python-based scan (baseline)
2. AUTO-FIX — Python metadata fixes (title, lang, DisplayDocTitle, MarkInfo)
3. RE-ASSESS — scan the auto-fixed version to see what improved
4. LOCAL EXTRACT — Extract text, images, tables using pdfplumber (no cloud API)
5. VISION ALT — Ollama local VLM generates alt text for images
6. REBUILD — Inject alt text and metadata into PDF
7. FINAL ASSESS — scan the rebuilt PDF
8. SORT — done/ (compliant) vs needs_review/ (remaining issues)
9. REPORT — comprehensive before/after comparison

Usage:
    python pipeline.py                    # Process all PDFs in input_pdfs/
    python pipeline.py --file myfile.pdf  # Process specific PDF
    python pipeline.py --skip-vision      # Skip Ollama alt text (use local extraction only)
    python pipeline.py --use-adobe        # Use old Adobe automation (deprecated, for testing)

Migration from Adobe workflow:
    OLD: python pipeline.py --skip-adobe  (still used local extraction fallback)
    NEW: python pipeline.py --skip-vision (uses local extraction + skips Ollama vision)
"""

import csv
import json
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import pikepdf
from pikepdf import Name, Dictionary


# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input_pdfs"
AUTO_FIXED_DIR = SCRIPT_DIR / "auto_fixed"
LOCAL_EXTRACTED_DIR = SCRIPT_DIR / "local_extracted"  # NEW: Local extraction output
ADOBE_FIXED_DIR = SCRIPT_DIR / "adobe_fixed"  # Kept for backward compat
ASSESSMENT_DIR = SCRIPT_DIR / "assessment_results"
DONE_DIR = SCRIPT_DIR / "done"
NEEDS_REVIEW_DIR = SCRIPT_DIR / "needs_review"
PIPELINE_REPORT_DIR = SCRIPT_DIR / "pipeline_results"
VISION_RESULTS_DIR = SCRIPT_DIR / "vision_results"
FIX_LOGS_DIR = SCRIPT_DIR / "fix_logs"


@dataclass
class PipelineStep:
    """Result from a single pipeline step."""
    step_name: str
    success: bool
    message: str
    issues_before: int = 0
    issues_after: int = 0
    details: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Complete pipeline result for a single PDF."""
    filename: str
    input_path: str
    final_path: str
    status: str  # "COMPLIANT", "NEEDS_REVIEW", "FAILED"
    steps: list = field(default_factory=list)
    baseline_issues: int = 0
    baseline_critical: int = 0
    after_python_fix_issues: int = 0
    after_extraction_issues: int = 0  # NEW: After local extraction
    remaining_issues: list = field(default_factory=list)
    extraction_method: str = "local"  # "local" or "adobe" (for reporting)


def import_auto_fix():
    """Import ada_auto_fix module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ada_auto_fix",
        SCRIPT_DIR / "ada_auto_fix.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_compliance_checker():
    """Import compliance_checker module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "compliance_checker",
        SCRIPT_DIR / "compliance_checker.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_local_extraction():
    """Import local extraction module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "local_extraction",
        SCRIPT_DIR / "local_extraction.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_local_pdf_builder():
    """Import local PDF builder module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "local_pdf_builder",
        SCRIPT_DIR / "local_pdf_builder.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def count_issues(pdf_path: Path) -> dict:
    """Quick issue count for a PDF using the compliance checker module."""
    from compliance_checker import run_compliance_check, remediation_summary
    report = run_compliance_check(pdf_path)
    rem = remediation_summary(report)

    # Extract image/table counts from check details
    image_count = 0
    table_count = 0
    is_tagged = False
    for check in report.checks:
        if isinstance(check, dict):
            details = check.get("details") or {}
            if check.get("check_id") == "WCAG-1.3.1-TAG" and check.get("status") == "PASS":
                is_tagged = True
            if "image_count" in details:
                image_count = details["image_count"]
            elif "total_xobjects" in details:
                image_count = details["total_xobjects"]
            if "total_tables" in details:
                table_count = details["total_tables"]

    return {
        "total_issues": report.failed + report.warnings,
        "critical": report.failed,
        "important": report.warnings,
        "moderate": 0,
        "advisory": 0,
        "auto_fixable": rem["auto_fixable"],
        "human_review": rem["human_review"],
        "manual_only": rem["manual_only"],
        "is_tagged": is_tagged,
        "image_count": image_count,
        "table_count": table_count,
    }


def run_python_assess(pdf_path: Path, step_label: str = "Assess") -> PipelineStep:
    """Run Python-based accessibility assessment."""
    try:
        issues = count_issues(pdf_path)
        return PipelineStep(
            step_name=step_label,
            success=True,
            message=f"Found {issues['total_issues']} issues ({issues['critical']} critical)",
            issues_before=issues['total_issues'],
            details=issues
        )
    except Exception as e:
        return PipelineStep(
            step_name=step_label,
            success=False,
            message=f"Assessment failed: {str(e)}"
        )


def run_python_auto_fix(input_path: Path, output_path: Path) -> PipelineStep:
    """Run Python auto-fix (metadata, MarkInfo)."""
    from ada_auto_fix import process_pdf
    result = process_pdf(input_path, output_path)

    fix_count = len(result.get("fixes_applied", []))
    return PipelineStep(
        step_name="Python Auto-Fix",
        success=result.get("success", False),
        message=f"Applied {fix_count} fixes" if result.get("success") else "Auto-fix failed",
        details=result
    )


def run_local_extraction_and_rebuild(
    input_path: Path,
    output_path: Path,
    skip_vision: bool = False
) -> PipelineStep:
    """
    NEW (Option A): Extract content locally and rebuild PDF with alt text.
    
    This replaces run_adobe_auto_fix() for the new workflow.
    Steps:
    1. Extract text, images, tables using pdfplumber
    2. Load Ollama alt text (if available and not skipped)
    3. Rebuild PDF with alt text and metadata
    """
    try:
        from local_extraction import extract_pdf_content, save_extraction_json
        from local_pdf_builder import rebuild_pdf_with_extraction, load_ollama_results
        
        print("  [3a] Extracting content with pdfplumber...")
        
        # Extract content locally
        extracted_content = extract_pdf_content(input_path, save_images=True)
        
        # Save extraction metadata for debugging
        extraction_json = output_path.parent / f"{output_path.stem}_extraction.json"
        save_extraction_json(extracted_content, extraction_json)
        
        # Load alt text from Ollama (if available)
        alt_text_data = None
        if not skip_vision:
            vision_json = VISION_RESULTS_DIR / f"{input_path.stem}_ollama_alt_text.json"
            if vision_json.exists():
                alt_text_data = load_ollama_results(vision_json)
                if alt_text_data:
                    print(f"  [3b] Loaded {len(alt_text_data)} alt text entries from Ollama")
            else:
                print(f"  Note: No Ollama alt text found at {vision_json}")
        
        # Rebuild PDF with extraction data + alt text
        print(f"  [3c] Rebuilding PDF with alt text...")
        rebuild_success = rebuild_pdf_with_extraction(
            input_path,
            extracted_content,
            alt_text_data=alt_text_data,
            output_pdf=output_path
        )
        
        messages = [
            f"Extracted {len(extracted_content.text_blocks)} text blocks",
            f"{len(extracted_content.images)} images",
            f"{len(extracted_content.tables)} tables"
        ]
        if alt_text_data:
            messages.append(f"Injected {len(alt_text_data)} alt texts")
        
        return PipelineStep(
            step_name="Local Extraction + Rebuild",
            success=rebuild_success,
            message="; ".join(messages),
            details={
                "text_blocks": len(extracted_content.text_blocks),
                "images": len(extracted_content.images),
                "tables": len(extracted_content.tables),
                "alt_texts_injected": len(alt_text_data) if alt_text_data else 0
            }
        )
    
    except Exception as e:
        return PipelineStep(
            step_name="Local Extraction + Rebuild",
            success=False,
            message=f"Extraction/rebuild failed: {str(e)}"
        )


def sort_pdf(pdf_path: Path, issues: dict, output_dir: Path) -> str:
    """
    Sort PDF into done/ or needs_review/ based on remaining issues.

    Returns: "COMPLIANT" or "NEEDS_REVIEW"
    """
    destination_dir: Path
    status: str

    # A PDF is "COMPLIANT" if it has zero auto-fixable issues
    # Issues that require human review (headings, tables, etc.) are OK
    if issues.get("auto_fixable", 0) == 0:
        destination_dir = DONE_DIR
        status = "COMPLIANT"
    else:
        destination_dir = NEEDS_REVIEW_DIR
        status = "NEEDS_REVIEW"

    destination_dir.mkdir(parents=True, exist_ok=True)
    dest_path = destination_dir / pdf_path.name

    shutil.copy2(pdf_path, dest_path)
    return status


def generate_pipeline_report(pipeline_results: list[PipelineResult]) -> Path:
    """Generate comprehensive pipeline report."""
    PIPELINE_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = PIPELINE_REPORT_DIR / f"pipeline_report_{timestamp}.csv"
    json_path = PIPELINE_REPORT_DIR / f"pipeline_report_{timestamp}.json"

    # CSV report
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Filename", "Status", "Baseline_Issues", "Baseline_Critical",
            "After_Python_Fix", "After_Extraction", "Remaining_Auto_Fixable",
            "Remaining_Human_Review", "Remaining_Manual", "Is_Tagged",
            "Image_Count", "Table_Count", "Extraction_Method"
        ])

        for pr in pipeline_results:
            final_issues = pr.remaining_issues if pr.remaining_issues else {}
            writer.writerow([
                pr.filename,
                pr.status,
                pr.baseline_issues,
                pr.baseline_critical,
                pr.after_python_fix_issues,
                pr.after_extraction_issues,
                final_issues.get("auto_fixable", 0),
                final_issues.get("human_review", 0),
                final_issues.get("manual_only", 0),
                final_issues.get("is_tagged", False),
                final_issues.get("image_count", 0),
                final_issues.get("table_count", 0),
                pr.extraction_method
            ])

    # JSON report (detailed)
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "total_processed": len(pipeline_results),
        "compliant": sum(1 for pr in pipeline_results if pr.status == "COMPLIANT"),
        "needs_review": sum(1 for pr in pipeline_results if pr.status == "NEEDS_REVIEW"),
        "failed": sum(1 for pr in pipeline_results if pr.status == "FAILED"),
        "extraction_method": "local (Option A)",
        "results": [asdict(pr) for pr in pipeline_results]
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)

    return report_path


def process_single_pdf(
    pdf_path: Path,
    skip_vision: bool = False,
    use_adobe: bool = False
) -> PipelineResult:
    """
    Run the full pipeline on a single PDF.
    
    Args:
        pdf_path: Path to input PDF
        skip_vision: Skip Ollama vision processing (use local extraction only)
        use_adobe: Use old Adobe automation (deprecated, for testing)
    """
    result = PipelineResult(
        filename=pdf_path.stem,
        input_path=str(pdf_path),
        final_path="",
        status="UNKNOWN",
        extraction_method="local"
    )

    print(f"\n{'='*70}")
    print(f"Processing: {pdf_path.name}")
    print(f"{'='*70}")

    # ========================================================
    # STEP 1: BASELINE ASSESSMENT
    # ========================================================
    print("\n[1/6] Baseline Assessment...")
    baseline = run_python_assess(pdf_path, "Baseline Assess")
    result.steps.append(baseline)
    result.baseline_issues = baseline.details.get("total_issues", 0)
    result.baseline_critical = baseline.details.get("critical", 0)
    print(f"      Issues: {result.baseline_issues} ({result.baseline_critical} critical)")

    # ========================================================
    # STEP 2: PYTHON AUTO-FIX
    # ========================================================
    print("\n[2/6] Python Auto-Fix (metadata, MarkInfo)...")
    AUTO_FIXED_DIR.mkdir(parents=True, exist_ok=True)
    python_fixed_path = AUTO_FIXED_DIR / pdf_path.name

    python_fix = run_python_auto_fix(pdf_path, python_fixed_path)
    result.steps.append(python_fix)

    if python_fix.success:
        # Re-assess the Python-fixed PDF
        print("\n[2b] Re-Assessing Python-Fixed PDF...")
        python_reassess = run_python_assess(python_fixed_path, "Python Re-Assess")
        result.steps.append(python_reassess)
        result.after_python_fix_issues = python_reassess.details.get("total_issues", 0)
        print(f"      Issues after Python fix: {result.after_python_fix_issues}")
    else:
        print("      Python auto-fix failed — continuing with original PDF")
        python_fixed_path = pdf_path
        result.after_python_fix_issues = result.baseline_issues

    # ========================================================
    # STEP 3: LOCAL EXTRACTION + ALT TEXT INJECTION
    # ========================================================
    print("\n[3/6] Local Extraction + Alt Text Injection...")
    LOCAL_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    extracted_path = LOCAL_EXTRACTED_DIR / pdf_path.name

    extraction_fix = run_local_extraction_and_rebuild(
        python_fixed_path,
        extracted_path,
        skip_vision=skip_vision
    )
    result.steps.append(extraction_fix)

    if extraction_fix.success:
        # Re-assess the extracted/rebuilt PDF
        print("\n[3d] Re-Assessing Rebuilt PDF...")
        extraction_reassess = run_python_assess(extracted_path, "Extraction Re-Assess")
        result.steps.append(extraction_reassess)
        result.after_extraction_issues = extraction_reassess.details.get("total_issues", 0)
        result.remaining_issues = extraction_reassess.details
        print(f"      Issues after extraction: {result.after_extraction_issues}")

        # Sort into done/ or needs_review/
        print("\n[4/6] Sorting PDF...")
        status = sort_pdf(extracted_path, extraction_reassess.details, extracted_path)
        result.status = status
        result.final_path = str(extracted_path)
        print(f"      → {status}")
    else:
        print("      Extraction failed — sorting Python-fixed PDF")
        status = sort_pdf(python_fixed_path, python_reassess.details, python_fixed_path)
        result.status = status
        result.final_path = str(python_fixed_path)
        result.after_extraction_issues = result.after_python_fix_issues

    # ========================================================
    # SUMMARY
    # ========================================================
    print(f"\n{'='*70}")
    print(f"SUMMARY: {pdf_path.name}")
    print(f"{'='*70}")
    print(f"  Baseline issues:      {result.baseline_issues}")
    print(f"  After Python fix:     {result.after_python_fix_issues}")
    print(f"  After extraction:     {result.after_extraction_issues}")
    print(f"  Final status:         {result.status}")
    print(f"  Final location:       {result.final_path}")
    print(f"  Extraction method:    {result.extraction_method} (Option A)")

    return result


def main():
    """Main entry point for the enhanced pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced PDF ADA Compliance Pipeline (Option A: Local Extraction)"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Process specific PDF file (default: all in input_pdfs/)"
    )
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help="Skip Ollama vision processing (use local extraction only)"
    )
    parser.add_argument(
        "--use-adobe",
        action="store_true",
        help="Use old Adobe automation (deprecated, for testing)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Enhanced PDF ADA Compliance Pipeline (Option A: Local Extraction)")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Skip Vision (Ollama): {args.skip_vision}")
    print(f"Use Adobe (deprecated): {args.use_adobe}")

    # Determine PDFs to process
    pdf_files = []
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}")
            return
        pdf_files = [args.file]
    else:
        if not INPUT_DIR.exists():
            print(f"Error: Input directory not found: {INPUT_DIR}")
            return
        pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in input_pdfs/")
        return

    print(f"\nFound {len(pdf_files)} PDF(s) to process")

    # Process each PDF
    pipeline_results = []
    for pdf_path in pdf_files:
        try:
            pr = process_single_pdf(
                pdf_path,
                skip_vision=args.skip_vision,
                use_adobe=args.use_adobe
            )
            pipeline_results.append(pr)
        except Exception as e:
            print(f"ERROR processing {pdf_path.name}: {str(e)}")
            pipeline_results.append(PipelineResult(
                filename=pdf_path.stem,
                input_path=str(pdf_path),
                final_path="",
                status="FAILED",
                steps=[PipelineStep(
                    step_name="Pipeline",
                    success=False,
                    message=str(e)
                )]
            ))

    # Generate report
    print(f"\n{'='*70}")
    print("Generating Pipeline Report...")
    report_path = generate_pipeline_report(pipeline_results)
    json_path = PIPELINE_REPORT_DIR / report_path.name.replace(".csv", ".json")
    print(f"  CSV:  {report_path}")
    print(f"  JSON: {json_path}")

    # Final summary
    compliant = sum(1 for pr in pipeline_results if pr.status == "COMPLIANT")
    needs_review = sum(1 for pr in pipeline_results if pr.status == "NEEDS_REVIEW")
    failed = sum(1 for pr in pipeline_results if pr.status == "FAILED")

    print(f"\n{'='*70}")
    print("PIPELINE COMPLETE (Option A: Local Extraction)")
    print(f"{'='*70}")
    print(f"  Total processed: {len(pipeline_results)}")
    print(f"  ✓ Compliant (done/):          {compliant}")
    print(f"  ⚠ Needs review (needs_review/): {needs_review}")
    print(f"  ✗ Failed:                     {failed}")
    print(f"\n  Output directories:")
    print(f"    done/              — {DONE_DIR}")
    print(f"    needs_review/      — {NEEDS_REVIEW_DIR}")
    print(f"    auto_fixed/        — {AUTO_FIXED_DIR}")
    print(f"    local_extracted/   — {LOCAL_EXTRACTED_DIR}  (NEW: Option A)")
    print(f"    pipeline_results/  — {PIPELINE_REPORT_DIR}")


if __name__ == "__main__":
    main()
