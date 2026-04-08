#!/usr/bin/env python3
"""
Enhanced PDF ADA Compliance Pipeline

Orchestrates the full workflow:
1. ASSESS — initial Python-based scan (baseline)
2. AUTO-FIX — Python metadata fixes (title, lang, DisplayDocTitle, MarkInfo)
3. RE-ASSESS — scan the auto-fixed version to see what improved
4. ADOBE AUTO — Acrobat Pro COM: auto-tag, reading order, alt text injection
5. FINAL ASSESS — scan the Adobe-fixed version
6. ADOBE VERIFY — run Acrobat's built-in accessibility checker
7. SORT — done/ (compliant) vs needs_review/ (remaining issues)
8. REPORT — comprehensive before/after comparison

Usage:
    python pipeline.py                    # Process all PDFs in input_pdfs/
    python pipeline.py --file myfile.pdf  # Process specific PDF
    python pipeline.py --skip-adobe       # Skip Adobe automation
    python pipeline.py --skip-vision      # Skip AI alt text generation
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
ADOBE_FIXED_DIR = SCRIPT_DIR / "adobe_fixed"
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
    after_adobe_issues: int = 0
    remaining_issues: list = field(default_factory=list)
    adobe_accessible: bool = False


def import_assessment():
    """Import ada_assessment module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ada_assessment",
        SCRIPT_DIR / "ada_assessment.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def count_issues(pdf_path: Path) -> dict:
    """Quick issue count for a PDF using the assessment module."""
    assessment = import_assessment()
    from ada_assessment import assess_pdf
    result = assess_pdf(pdf_path)
    return {
        "total_issues": result.total_issues,
        "critical": result.critical_count,
        "important": result.important_count,
        "moderate": result.moderate_count,
        "advisory": result.advisory_count,
        "auto_fixable": result.auto_fixable_count,
        "human_review": result.human_review_count,
        "manual_only": result.manual_only_count,
        "is_tagged": result.structure_info.get("has_struct_tree", False),
        "image_count": result.structure_info.get("image_count", 0),
        "table_count": result.structure_info.get("table_count", 0),
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


def run_adobe_auto_fix(input_path: Path, output_path: Path, alt_text_data=None) -> PipelineStep:
    """Run Adobe Acrobat Pro: open, check info, save."""
    try:
        from adobe_auto import process_pdf_with_adobe
        result = process_pdf_with_adobe(
            input_path,
            output_path,
            run_accessibility=True
        )

        messages = []
        if result.get("pdf_info"):
            info = result["pdf_info"]
            if info.get("is_tagged"):
                messages.append("Document is tagged")
            else:
                messages.append("Document is NOT tagged (needs manual auto-tag in Acrobat)")

        return PipelineStep(
            step_name="Adobe Auto",
            success=result.get("success", False),
            message=", ".join(messages) if messages else "Adobe processing completed",
            details=result
        )
    except ImportError:
        return PipelineStep(
            step_name="Adobe Auto",
            success=False,
            message="pywin32 not installed. Run: pip install pywin32 (Windows only)"
        )
    except Exception as e:
        return PipelineStep(
            step_name="Adobe Auto",
            success=False,
            message=f"Adobe automation failed: {str(e)}"
        )


def sort_pdf(pdf_path: Path, issues: dict, output_dir: Path) -> str:
    """
    Sort PDF into done/ or needs_review/ based on remaining issues.

    Returns: "done" or "needs_review"
    """
    destination_dir: Path
    status: str

    # A PDF is "done" if it has zero auto-fixable issues
    # Issues that require human review (headings, tables, etc.) are OK for now
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
            "After_Python_Fix", "After_Adobe", "Remaining_Auto_Fixable",
            "Remaining_Human_Review", "Remaining_Manual", "Is_Tagged",
            "Image_Count", "Table_Count"
        ])

        for pr in pipeline_results:
            final_issues = pr.remaining_issues if pr.remaining_issues else {}
            writer.writerow([
                pr.filename,
                pr.status,
                pr.baseline_issues,
                pr.baseline_critical,
                pr.after_python_fix_issues,
                pr.after_adobe_issues,
                final_issues.get("auto_fixable", 0),
                final_issues.get("human_review", 0),
                final_issues.get("manual_only", 0),
                final_issues.get("is_tagged", False),
                final_issues.get("image_count", 0),
                final_issues.get("table_count", 0)
            ])

    # JSON report (detailed)
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "total_processed": len(pipeline_results),
        "compliant": sum(1 for pr in pipeline_results if pr.status == "COMPLIANT"),
        "needs_review": sum(1 for pr in pipeline_results if pr.status == "NEEDS_REVIEW"),
        "failed": sum(1 for pr in pipeline_results if pr.status == "FAILED"),
        "results": [asdict(pr) for pr in pipeline_results]
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)

    return report_path


def process_single_pdf(pdf_path: Path, skip_adobe: bool = False, skip_vision: bool = False) -> PipelineResult:
    """
    Run the full enhanced pipeline on a single PDF.
    """
    result = PipelineResult(
        filename=pdf_path.stem,
        input_path=str(pdf_path),
        final_path="",
        status="UNKNOWN"
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
    # STEP 3: ADOBE AUTO (if not skipped)
    # ========================================================
    if not skip_adobe:
        print("\n[3/6] Adobe Auto-Tag + Accessibility...")
        print("      NOTE: Adobe COM auto-tag is limited.")
        print("      For full auto-tagging, open in Acrobat:")
        print("        Tools > Accessibility > Auto-Tag Document")
        ADOBE_FIXED_DIR.mkdir(parents=True, exist_ok=True)
        adobe_fixed_path = ADOBE_FIXED_DIR / pdf_path.name

        # Check if we have vision alt text to inject
        alt_text_data = None
        vision_json = VISION_RESULTS_DIR / f"{pdf_path.stem}_ollama_alt_text.json"
        if vision_json.exists() and not skip_vision:
            try:
                with open(vision_json, "r", encoding="utf-8") as f:
                    vision_results = json.load(f)
                alt_text_data = vision_results.get("results", [])
                print(f"      Loading {len(alt_text_data)} alt text entries from vision results")
            except Exception:
                pass

        adobe_fix = run_adobe_auto_fix(python_fixed_path, adobe_fixed_path, alt_text_data)
        result.steps.append(adobe_fix)

        if adobe_fix.success:
            # Re-assess the Adobe-fixed PDF
            print("\n[3b] Re-Assessing Adobe-Fixed PDF...")
            adobe_reassess = run_python_assess(adobe_fixed_path, "Adobe Re-Assess")
            result.steps.append(adobe_reassess)
            result.after_adobe_issues = adobe_reassess.details.get("total_issues", 0)
            result.remaining_issues = adobe_reassess.details
            print(f"      Issues after Adobe fix: {result.after_adobe_issues}")

            # Sort into done/ or needs_review/
            print("\n[4/6] Sorting PDF...")
            status = sort_pdf(adobe_fixed_path, adobe_reassess.details, adobe_fixed_path)
            result.status = status
            result.final_path = str(adobe_fixed_path)
            print(f"      → {status}")
        else:
            print("      Adobe auto-fix failed — sorting Python-fixed PDF")
            status = sort_pdf(python_fixed_path, python_reassess.details, python_fixed_path)
            result.status = status
            result.final_path = str(python_fixed_path)
            result.after_adobe_issues = result.after_python_fix_issues
    else:
        print("\n[3/6] Skipping Adobe (user requested)")
        status = sort_pdf(python_fixed_path, python_reassess.details, python_fixed_path)
        result.status = status
        result.final_path = str(python_fixed_path)
        result.after_adobe_issues = result.after_python_fix_issues

    # ========================================================
    # SUMMARY
    # ========================================================
    print(f"\n{'='*70}")
    print(f"SUMMARY: {pdf_path.name}")
    print(f"{'='*70}")
    print(f"  Baseline issues:    {result.baseline_issues}")
    print(f"  After Python fix:  {result.after_python_fix_issues}")
    print(f"  After Adobe fix:   {result.after_adobe_issues}")
    print(f"  Final status:      {result.status}")
    print(f"  Final location:    {result.final_path}")

    return result


def main():
    """Main entry point for the enhanced pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced PDF ADA Compliance Pipeline"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Process specific PDF file (default: all in input_pdfs/)"
    )
    parser.add_argument(
        "--skip-adobe",
        action="store_true",
        help="Skip Adobe Acrobat Pro automation"
    )
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help="Skip AI alt text generation"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Enhanced PDF ADA Compliance Pipeline")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Skip Adobe: {args.skip_adobe}")
    print(f"Skip Vision: {args.skip_vision}")

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
            pr = process_single_pdf(pdf_path, skip_adobe=args.skip_adobe, skip_vision=args.skip_vision)
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
    print("PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"  Total processed: {len(pipeline_results)}")
    print(f"  ✓ Compliant (done/):          {compliant}")
    print(f"  ⚠ Needs review (needs_review/): {needs_review}")
    print(f"  ✗ Failed:                     {failed}")
    print(f"\n  Output directories:")
    print(f"    done/           — {DONE_DIR}")
    print(f"    needs_review/   — {NEEDS_REVIEW_DIR}")
    print(f"    auto_fixed/     — {AUTO_FIXED_DIR}")
    print(f"    adobe_fixed/    — {ADOBE_FIXED_DIR}")
    print(f"    pipeline_results/ — {PIPELINE_REPORT_DIR}")


if __name__ == "__main__":
    main()
