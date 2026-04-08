#!/usr/bin/env python3
"""
Deep Scan Runner — calls compliance_checker on multiple PDFs and outputs JSON.
Used by the web UI /api/deep-scan endpoint.
"""

import json
import sys
from pathlib import Path

# Import the compliance checker
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from compliance_checker import run_compliance_check, generate_compliance_summary


def deep_scan_all(pdf_dir: str) -> dict:
    """Scan all PDFs in a directory and return structured results."""
    pdf_path = Path(pdf_dir)
    if not pdf_path.exists():
        return {"error": f"Directory not found: {pdf_dir}"}

    pdfs = list(pdf_path.glob("*.pdf"))
    if not pdfs:
        return {"error": "No PDF files found"}

    results = []
    for pdf_file in pdfs:
        try:
            report = run_compliance_check(pdf_file)
            summary = generate_compliance_summary(report)

            # Build structured guidance
            failed_checks = [c for c in report.checks if c["status"] == "FAIL"]
            warning_checks = [c for c in report.checks if c["status"] == "WARNING"]
            manual_checks = [c for c in report.checks if c["status"] == "MANUAL_CHECK"]
            passed_checks = [c for c in report.checks if c["status"] == "PASS"]

            guidance = []
            for check in failed_checks + warning_checks + manual_checks:
                g = {
                    "check_id": check["check_id"],
                    "name": check["name"],
                    "status": check["status"],
                    "wcag": check["wcag_criteria"],
                    "pdfua": check["pdfua_section"],
                    "description": check["description"],
                    "recommendation": check["recommendation"],
                    "adobe_fix": _get_adobe_fix_instructions(check),
                    "auto_fixable": _is_auto_fixable(check),
                    "severity": "FAIL" if check["status"] == "FAIL" else "WARN"
                }
                guidance.append(g)

            results.append({
                "filename": pdf_file.name,
                "wcag_level_a_pass": report.wcag_level_a_pass,
                "pdfua_compliant": report.pdfua_compliant,
                "section508_compliant": report.section508_compliant,
                "passed": report.passed,
                "failed": report.failed,
                "warnings": report.warnings,
                "manual_checks": report.manual_checks,
                "guidance": guidance,
                "summary": summary
            })
        except Exception as e:
            results.append({
                "filename": pdf_file.name,
                "error": str(e)
            })

    return {
        "total_files": len(pdfs),
        "scanned": len(results),
        "results": results
    }


def _is_auto_fixable(check: dict) -> bool:
    """Determine if this check can be auto-fixed by our pipeline."""
    auto_fixable_ids = [
        "WCAG-2.4.2",       # Title
        "WCAG-3.1.1",       # Language
        "WCAG-2.4.2-DT",    # DisplayDocTitle
        "PDFUA-5.3",        # MarkInfo
    ]
    return check["check_id"] in auto_fixable_ids


def _get_adobe_fix_instructions(check: dict) -> str:
    """Get step-by-step Adobe Acrobat fix instructions."""
    instructions = {
        "WCAG-1.3.1-TAG": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Accessibility > Auto-Tag Document\n"
            "3. Review and fix any tagging errors\n"
            "4. Save the document"
        ),
        "PDFUA-5.3": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to File > Properties > Advanced\n"
            "3. Check 'Document is Tagged'\n"
            "4. Save the document"
        ),
        "WCAG-2.4.2": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to File > Properties > Description\n"
            "3. Enter a meaningful Title\n"
            "4. Save the document"
        ),
        "WCAG-3.1.1": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to File > Properties > Advanced\n"
            "3. Set Language to 'en-US' (or appropriate)\n"
            "4. Save the document"
        ),
        "WCAG-2.4.2-DT": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to File > Properties > Initial View\n"
            "3. Under 'Show', select 'Document Title'\n"
            "4. Save the document"
        ),
        "WCAG-2.4.6-H": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Accessibility > Tags\n"
            "3. Expand the Tags tree\n"
            "4. Right-click headings > Properties > Type\n"
            "5. Set correct heading level (H1, H2, etc.)\n"
            "6. Ensure H1 is the document title\n"
            "7. Save the document"
        ),
        "WCAG-1.1.1-IMG": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Accessibility > Tags\n"
            "3. Find each /Figure element in the tags tree\n"
            "4. Right-click > Properties > Alternate Text\n"
            "5. Enter descriptive alt text\n"
            "6. Mark decorative images as 'Artifact'\n"
            "7. Save the document"
        ),
        "WCAG-1.3.2": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Accessibility > Reading Order\n"
            "3. Review the numbered order overlay\n"
            "4. Drag to reorder if incorrect\n"
            "5. Save the document"
        ),
        "WCAG-1.3.1-TBL": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Accessibility > Table Editor\n"
            "3. Select header cells\n"
            "4. Right-click > Table Cell Properties\n"
            "5. Check 'Header cell'\n"
            "6. Set scope (row/column) if needed\n"
            "7. Save the document"
        ),
        "WCAG-1.3.1-LIST": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Accessibility > Tags\n"
            "3. Find list elements\n"
            "4. Ensure structure is: L > LI > Lbl + LBody\n"
            "5. Fix any missing elements\n"
            "6. Save the document"
        ),
        "WCAG-2.4.4-LINK": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Accessibility > Tags\n"
            "3. Find link annotations\n"
            "4. Right-click > Properties > Alternate Text\n"
            "5. Enter descriptive text (avoid 'click here')\n"
            "6. Save the document"
        ),
        "WCAG-4.1.2-FORM": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to Tools > Prepare Form\n"
            "3. Right-click each form field > Properties\n"
            "4. Enter a Tooltip (accessible name)\n"
            "5. Ensure fields are tagged\n"
            "6. Save the document"
        ),
        "SEC-508": (
            "1. Open PDF in Adobe Acrobat Pro\n"
            "2. Go to File > Properties > Security\n"
            "3. Change Security Method to 'No Security'\n"
            "4. Save the document"
        ),
    }
    return instructions.get(check["check_id"],
        "Manual review required in Adobe Acrobat:\n"
        "1. Open PDF in Adobe Acrobat Pro\n"
        "2. Go to Tools > Accessibility > Accessibility Check\n"
        "3. Review the flagged issue and fix manually"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deep_scan.py <pdf_dir>")
        sys.exit(1)

    pdf_dir = sys.argv[1]
    result = deep_scan_all(pdf_dir)
    print(json.dumps(result, indent=2))
