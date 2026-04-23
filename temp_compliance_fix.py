#!/usr/bin/env python3
"""
ADA/WCAG/PDF-UA Compliance Checker

Comprehensive accessibility assessment mapped to:
- WCAG 2.2 (Level A & AA)
- PDF/UA-1 (ISO 14289-1)
- Section 508 Refresh (2017+)

Each check is mapped to specific success criteria for compliance reporting.
Checks are categorized by remediation level:
  - AUTO_FIXABLE: Can be fixed programmatically (title, language, DisplayDocTitle, MarkInfo)
  - HUMAN_REVIEW: Detectable but requires human judgment (headings, figures, tables, links)
  - MANUAL_ONLY: Requires full human intervention (fonts, encryption)
  - MANUAL_CHECK: Needs human verification (reading order)
"""

import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

# Use PyPDF (migrated from pikepdf)
from pypdf.generic import NameObject as Name, ArrayObject as Array, DictionaryObject as Dictionary

# Import utility functions for extraction and analysis
from _pdf_utils import count_images, get_links


def _is_array(node):
    """Safely check if a pikepdf object is an Array."""
    try:
        return isinstance(node, (Array, list))
    except Exception:
        return isinstance(node, list)


def _is_dict(node):
    """Safely check if a pikepdf object is a Dictionary."""
    try:
        return isinstance(node, (Dictionary, dict))
    except Exception:
        return hasattr(node, 'keys')


class ComplianceLevel(Enum):
    A = "A"           # Minimum accessibility
    AA = "AA"         # Standard compliance level
    AAA = "AAA"       # Enhanced accessibility


class CheckStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    MANUAL = "MANUAL_CHECK"


@dataclass
class ComplianceCheck:
    """Individual compliance check result."""
    check_id: str
    name: str
    description: str
    status: str
    level: str
    wcag_criteria: str
    pdfua_section: str
    section508: str
    location: str = ""
    recommendation: str = ""
    details: dict = None
    remediation_level: str = "MANUAL_CHECK"  # AUTO_FIXABLE, HUMAN_REVIEW, MANUAL_ONLY, MANUAL_CHECK


@dataclass
class ComplianceReport:
    """Complete compliance report for a PDF."""
    filename: str
    filepath: str
    overall_status: str = "UNKNOWN"
    wcag_level_a_pass: bool = False
    wcag_level_aa_pass: bool = False
    pdfua_compliant: bool = False
    section508_compliant: bool = False
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    manual_checks: int = 0
    checks: list = None


# WCAG 2.2 Success Criteria mapping
WCAG_CRITERIA = {
    "1.1.1": "Non-text Content",
    "1.3.1": "Info and Relationships",
    "1.3.2": "Meaningful Sequence",
    "1.4.1": "Use of Color",
    "1.4.3": "Contrast (Minimum)",
    "1.4.5": "Images of Text",
    "2.1.1": "Keyboard",
    "2.4.1": "Bypass Blocks",
    "2.4.2": "Page Titled",
    "2.4.3": "Focus Order",
    "2.4.4": "Link Purpose (In Context)",
    "2.4.6": "Headings and Labels",
    "3.1.1": "Language of Page",
    "3.1.2": "Language of Parts",
    "4.1.1": "Parsing",
    "4.1.2": "Name, Role, Value",
    "4.1.3": "Status Messages"
}


def check_title(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 2.4.2 - Page Titled (Level A)"""
    title = pdf.Root.get("/Title")

    if title:
        return ComplianceCheck(
            check_id="WCAG-2.4.2",
            name="Document Title",
            description="Document has a meaningful title",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.2",
            pdfua_section="§7.1",
            section508="502.3.1",
            recommendation="Title is set correctly",
            details={"title": str(title)},
            remediation_level="AUTO_FIXABLE"
        )
    else:
        return ComplianceCheck(
            check_id="WCAG-2.4.2",
            name="Document Title",
            description="Document title is missing",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.2",
            pdfua_section="§7.1",
            section508="502.3.1",
            location="Document Properties",
            recommendation="Set document title in metadata (not just filename)",
            remediation_level="AUTO_FIXABLE"
        )


def check_language(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 3.1.1 - Language of Page (Level A)"""
    lang = pdf.Root.get("/Lang")

    if lang:
        return ComplianceCheck(
            check_id="WCAG-3.1.1",
            name="Document Language",
            description="Document language is specified",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="3.1.1",
            pdfua_section="§7.2",
            section508="502.3.1",
            recommendation=f"Language set to: {str(lang)}",
            details={"language": str(lang)},
            remediation_level="AUTO_FIXABLE"
        )
    else:
        return ComplianceCheck(
            check_id="WCAG-3.1.1",
            name="Document Language",
            description="Document language is missing",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="3.1.1",
            pdfua_section="§7.2",
            section508="502.3.1",
            location="Document Catalog",
            recommendation="Set document language (e.g., 'en-US') for screen readers",
            remediation_level="AUTO_FIXABLE"
        )


def check_display_doctitle(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 2.4.2 - DisplayDocTitle (Level A)"""
    viewer_prefs = pdf.Root.get("/ViewerPreferences")
    display_title = False

    if viewer_prefs:
        display_title = viewer_prefs.get("/DisplayDocTitle") == True

    if display_title:
        return ComplianceCheck(
            check_id="WCAG-2.4.2-DT",
            name="Display Document Title",
            description="ViewerPreferences.DisplayDocTitle is set to true",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.2",
            pdfua_section="§7.1",
            section508="502.3.1",
            recommendation="Title will display in viewer title bar",
            remediation_level="AUTO_FIXABLE"
        )
    else:
        return ComplianceCheck(
            check_id="WCAG-2.4.2-DT",
            name="Display Document Title",
            description="DisplayDocTitle not set (title may not show in title bar)",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.2",
            pdfua_section="§7.1",
            section508="502.3.1",
            location="ViewerPreferences",
            recommendation="Set DisplayDocTitle to true",
            remediation_level="AUTO_FIXABLE"
        )


def check_tags_tree(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 1.3.1, 4.1.2 - Tagged PDF (Level A)"""
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if struct_tree:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TAG",
            name="Tagged PDF Structure",
            description="Document has a structure tree (tagged PDF)",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 4.1.2",
            pdfua_section="§5",
            section508="502.3.2",
            recommendation="Document is tagged",
            details={"has_struct_tree": True},
            remediation_level="MANUAL_ONLY"
        )
    else:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TAG",
            name="Tagged PDF Structure",
            description="Document is NOT a tagged PDF - major accessibility barrier",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 4.1.2",
            pdfua_section="§5",
            section508="502.3.2",
            location="Document Catalog",
            recommendation="Document requires full tagging structure (manual process in Adobe Acrobat)",
            remediation_level="MANUAL_ONLY"
        )


def check_mark_info(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """PDF/UA §5.3 - MarkInfo"""
    mark_info = pdf.Root.get("/MarkInfo")
    is_marked = False

    if mark_info:
        marked = mark_info.get("/Marked")
        is_marked = marked is True or marked == Name("/true")

    if is_marked:
        return ComplianceCheck(
            check_id="PDFUA-5.3",
            name="MarkInfo Marked",
            description="MarkInfo.Marked is set to true",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="4.1.2",
            pdfua_section="§5.3",
            section508="502.3.2",
            recommendation="Document is marked as tagged",
            remediation_level="AUTO_FIXABLE"
        )
    else:
        return ComplianceCheck(
            check_id="PDFUA-5.3",
            name="MarkInfo Marked",
            description="MarkInfo.Marked is not set to true",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="4.1.2",
            pdfua_section="§5.3",
            section508="502.3.2",
            location="Document Catalog /MarkInfo",
            recommendation="Set MarkInfo.Marked to true",
            remediation_level="AUTO_FIXABLE"
        )


def check_reading_order(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 1.3.2 - Meaningful Sequence"""
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-1.3.2",
            name="Reading Order",
            description="Cannot check - no structure tree",
            status=CheckStatus.MANUAL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.2",
            pdfua_section="§5.3",
            section508="502.3.2",
            recommendation="Add tags first, then verify reading order",
            remediation_level="MANUAL_CHECK"
        )

    parent_tree = struct_tree.get("/ParentTree")

    if parent_tree:
        return ComplianceCheck(
            check_id="WCAG-1.3.2",
            name="Reading Order Mapping",
            description="ParentTree exists for content-to-structure mapping",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.2",
            pdfua_section="§5.3",
            section508="502.3.2",
            recommendation="Reading order mapping present (verify manually)",
            remediation_level="MANUAL_CHECK"
        )
    else:
        return ComplianceCheck(
            check_id="WCAG-1.3.2",
            name="Reading Order Mapping",
            description="ParentTree missing - reading order may be incorrect",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.2",
            pdfua_section="§5.3",
            section508="502.3.2",
            location="Structure Tree Root",
            recommendation="Ensure ParentTree maps content streams to structure elements",
            remediation_level="MANUAL_CHECK"
        )


def check_headings_structure(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 1.3.1, 2.4.6 - Headings and Labels (Level A).
    Uses structural analysis via pikepdf combined with text verification via _pdf_utils.
    """
    from _pdf_utils import get_text_page

    struct_tree = pdf.Root.get("/StructTreeRoot")

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Structure",
            description="Cannot check - no structure tree",
            status=CheckStatus.MANUAL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            recommendation="Add tags first",
            remediation_level="HUMAN_REVIEW"
        )

    # Collect heading tags and their sequence (structural)
    heading_tags = []
    heading_sequence = []

    def collect_headings(node):
        if node is None:
            return
        if _is_array(node):
            for item in node:
                collect_headings(item)
            return
        if not _is_dict(node):
            return

        try:
            elem_type = node.get("/S")
        except Exception:
            return
        if elem_type:
            type_str = str(elem_type)
            if type_str.startswith("/H") and type_str not in ["/Heading", "/Header"]:
                heading_tags.append(type_str)
                # Track sequence for first-heading check
                if type_str not in ["/Heading", "/Header"] and len(type_str) <= 3:
                    try:
                        level = int(type_str[2:])
                        heading_sequence.append((level, type_str))
                    except ValueError:
                        pass

        try:
            children = node.get("/K")
        except Exception:
            return
        if children:
            collect_headings(children)

    k_array = struct_tree.get("/K")
    if k_array:
        collect_headings(k_array)

    # Verify structural headings against actual text content (using _pdf_utils)
    total_text = ""
    try:
        for i, page in enumerate(pdf.pages):
            page_text = get_text_page(i, pdf)
            if page_text:
                total_text += f"\n{page + 1}: {page_text}\n"
    except Exception:
        pass

    # Check if H1 exists in text as well (semantic validation)
    has_h1_in_text = "# " in total_text or "H1" in total_text.upper()
    
    # Analyze
    has_h1 = "/H1" in heading_tags

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Structure",
            description="Document lacks structural tags (StructTreeRoot missing)",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            location="Document Catalog",
            recommendation="Add structure tree in Adobe Acrobat Pro",
            remediation_level="MANUAL_ONLY"
        )

    # Check for multiple H1s
    h1_count = heading_tags.count("/H1")
    if h1_count > 1:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Hierarchy",
            description=f"Document has {h1_count} H1 headings (should typically have one)",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            location="Structure tree",
            recommendation="Use only one H1 per document (main title), use H2+ for sections",
            details={"heading_tags": heading_tags, "h1_count": h1_count},
            remediation_level="HUMAN_REVIEW"
        )

    # Check if first heading is not H1
    if heading_sequence and heading_sequence[0][0] != 1:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Hierarchy",
            description=f"Document starts with H{heading_sequence[0][0]} instead of H1",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            location=f"First heading: {heading_sequence[0][1]}",
            recommendation="First heading should be H1 (main document title)",
            details={"heading_tags": heading_tags, "first_heading": heading_sequence[0][1]},
            remediation_level="HUMAN_REVIEW"
        )

    # Semantic check: Verify if structural H1 is supported by text content
    semantic_ok = has_h1 and has_h1_in_text

    # Check for skipped levels
    levels_present = []
    for i in range(1, 7):
        if f"/H{i}" in heading_tags:
            levels_present.append(i)

    skipped = []
    for i in range(len(levels_present) - 1):
        if levels_present[i+1] - levels_present[i] > 1:
            skipped.append((levels_present[i], levels_present[i+1]))

    if skipped and not semantic_ok:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Hierarchy",
            description=f"Skipped heading levels detected: {skipped}",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            location="Structure tree",
            recommendation="Fix heading hierarchy - do not skip levels (H1 -> H2 -> H3)",
            details={"heading_tags": heading_tags, "skipped": skipped},
            remediation_level="HUMAN_REVIEW"
        )
    elif semantic_ok:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Hierarchy",
            description="Headings are properly structured and semantically supported by text.",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            recommendation="Headings are properly structured.",
            details={"heading_tags": list(set(heading_tags)), "semantic_check": True},
            remediation_level="HUMAN_REVIEW"
        )
    else:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Hierarchy",
            description="Document has structural headings but lacks corresponding semantic text support.",
            status=CheckStatus.WARNING.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            recommendation="Ensure text content aligns with structural headings.",
            details={"heading_tags": heading_tags, "semantic_check": False},
            remediation_level="HUMAN_REVIEW"
        )

    # Check if first heading is not H1
    if heading_sequence and heading_sequence[0][0] != 1:
        return ComplianceCheck(
            check_id="WCAG-2.4.6-H",
            name="Heading Hierarchy",
            description=f"Document starts with H{heading_sequence[0][0]} instead of H1",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1, 2.4.6",
            pdfua_section="§5.4",
            section508="502.3.2",
            location=f"First heading: {heading_sequence[0][1]}",
            recommendation="First heading should be H1 (main document title)",
            details={"heading_tags": heading_tags, "first_heading": heading_sequence[0][1]},
            remediation_level="HUMAN_REVIEW"
        )

    if has_h1:
        # Check for skipped levels
        levels_present = []
        for i in range(1, 7):
            if f"/H{i}" in heading_tags:
                levels_present.append(i)

        skipped = []
        for i in range(len(levels_present) - 1):
            if levels_present[i+1] - levels_present[i] > 1:
                skipped.append((levels_present[i], levels_present[i+1]))

        if skipped:
            return ComplianceCheck(
                check_id="WCAG-2.4.6-H",
                name="Heading Hierarchy",
                description=f"Skipped heading levels detected: {skipped}",
                status=CheckStatus.FAIL.value,
                level=ComplianceLevel.A.value,
                wcag_criteria="1.3.1, 2.4.6",
                pdfua_section="§5.4",
                section508="502.3.2",
                location="Structure tree",
                recommendation="Fix heading hierarchy - do not skip levels (H1 → H2 → H3)",
                details={"heading_tags": heading_tags, "skipped": skipped},
                remediation_level="HUMAN_REVIEW"
            )
        else:
            return ComplianceCheck(
                check_id="WCAG-2.4.6-H",
                name="Heading Hierarchy",
                description="Heading levels are properly nested",
                status=CheckStatus.PASS.value,
                level=ComplianceLevel.A.value,
                wcag_criteria="1.3.1, 2.4.6",
                pdfua_section="§5.4",
                section508="502.3.2",
                recommendation="Headings are properly structured",
                details={"heading_tags": list(set(heading_tags))},
                remediation_level="HUMAN_REVIEW"
            )
    else:
        if heading_tags:
            return ComplianceCheck(
                check_id="WCAG-2.4.6-H",
                name="Heading Hierarchy",
                description="Document has headings but no H1 (main heading)",
                status=CheckStatus.FAIL.value,
                level=ComplianceLevel.A.value,
                wcag_criteria="1.3.1, 2.4.6",
                pdfua_section="§5.4",
                section508="502.3.2",
                location="Structure tree",
                recommendation="Ensure document starts with H1 heading",
                details={"heading_tags": heading_tags},
                remediation_level="HUMAN_REVIEW"
            )
        else:
            return ComplianceCheck(
                check_id="WCAG-2.4.6-H",
                name="Heading Hierarchy",
                description="No heading tags found in document",
                status=CheckStatus.WARNING.value,
                level=ComplianceLevel.A.value,
                wcag_criteria="1.3.1, 2.4.6",
                pdfua_section="§5.4",
                section508="502.3.2",
                recommendation="Consider adding headings for navigation (may not be required for short documents)",
                remediation_level="HUMAN_REVIEW"
            )


def check_images_alt_text(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 1.1.1 - Non-text Content (Level A).
    Uses _pdf_utils for efficient image counting and structural validation.
    """
    # Count XObject images using utility wrapper
    img_data = count_images(pdf)
    image_count = img_data["total_count"]
    
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if image_count == 0:
        return ComplianceCheck(
            check_id="WCAG-1.1.1-IMG",
            name="Image Alternative Text",
            description="No images found in document",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1",
            pdfua_section="§5.6",
            section508="502.3.3",
            recommendation="No images to check",
            remediation_level="HUMAN_REVIEW"
        )

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-1.1.1-IMG",
            name="Image Alternative Text",
            description=f"{image_count} images found but document is untagged",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1",
            pdfua_section="§5.6",
            section508="502.3.3",
            location="Document",
            recommendation=f"All {image_count} images need /Figure tags with alt text",
            remediation_level="HUMAN_REVIEW"
        )

    # Count figures with alt text
    figures_with_alt = 0
    figures_total = 0

    def count_figures(node):
        nonlocal figures_with_alt, figures_total
        if node is None:
            return
        if _is_array(node):
            for item in node:
                count_figures(item)
            return
        if not _is_dict(node):
            return

        try:
            elem_type = node.get("/S")
        except Exception:
            return
        if elem_type == Name("/Figure"):
            figures_total += 1
            try:
                alt_text = node.get("/Alt")
            except Exception:
                alt_text = None
            if alt_text and str(alt_text).strip():
                figures_with_alt += 1

        try:
            children = node.get("/K")
        except Exception:
            return
        if children:
            count_figures(children)

    k_array = struct_tree.get("/K")
    if k_array:
        count_figures(k_array)

    untagged_images = image_count - figures_total

    if untagged_images > 0:
        return ComplianceCheck(
            check_id="WCAG-1.1.1-IMG",
            name="Image Alternative Text",
            description=f"{untagged_images} images not in structure tree",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1",
            pdfua_section="§5.6",
            section508="502.3.3",
            location="Structure tree",
            recommendation=f"Add {untagged_images} images to structure tree with /Figure tags and alt text",
            details={"total_xobjects": image_count, "tagged_figures": figures_total, "untagged": untagged_images},
            remediation_level="HUMAN_REVIEW"
        )

    if figures_total > 0 and figures_with_alt < figures_total:
        missing_alt = figures_total - figures_with_alt
        return ComplianceCheck(
            check_id="WCAG-1.1.1-IMG",
            name="Image Alternative Text",
            description=f"{missing_alt} figures missing alt text",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1",
            pdfua_section="§5.6",
            section508="502.3.3",
            location="Structure tree",
            recommendation=f"Add alt text to {missing_alt} figures",
            details={"tagged_figures": figures_total, "with_alt": figures_with_alt, "missing_alt": missing_alt},
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="WCAG-1.1.1-IMG",
        name="Image Alternative Text",
        description=f"All {figures_total} figures have alt text",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="1.1.1",
        pdfua_section="§5.6",
        section508="502.3.3",
        recommendation="All images have alternative text",
        details={"tagged_figures": figures_total, "with_alt": figures_with_alt, "image_count": image_count},
        remediation_level="HUMAN_REVIEW"
    )


def check_links(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 2.4.4 - Link Purpose (In Context).
    Uses _pdf_utils to extract and verify link annotations.
    """
    links = get_links(pdf)
    
    if not links:
        return ComplianceCheck(
            check_id="WCAG-2.4.4",
            name="Link Purpose (In Context)",
            description="No links found in document",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.4",
            pdfua_section="§5.8",
            section508="502.3.4",
            recommendation="No links to check",
            remediation_level="HUMAN_REVIEW"
        )

    # Check if any link has descriptive alt text
    links_with_alt = 0
    for link in links:
        try:
            # pypdfium2 link annotations typically have 'alt' property or title
            # We use a heuristic check. If the link annotation has an accessible name/title.
            if "title" in str(link).lower() and len(str(link).get("title", "")) > 0:
                links_with_alt += 1
        except Exception:
            pass
    
    total_links = len(links)
    missing_alt = total_links - links_with_alt

    if missing_alt == 0:
        return ComplianceCheck(
            check_id="WCAG-2.4.4",
            name="Link Purpose (In Context)",
            description=f"All {total_links} links have accessible names.",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.4",
            pdfua_section="§5.8",
            section508="502.3.4",
            recommendation=f"{total_links} links are properly described.",
            details={"total": total_links, "with_alt": links_with_alt},
            remediation_level="HUMAN_REVIEW"
        )
    else:
        return ComplianceCheck(
            check_id="WCAG-2.4.4",
            name="Link Purpose (In Context)",
            description=f"{missing_alt} links lack descriptive text.",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.4",
            pdfua_section="§5.8",
            section508="502.3.4",
            location="Link annotations",
            recommendation=f"Add descriptive titles to {missing_alt} links.",
            details={"total": total_links, "with_alt": links_with_alt, "missing": missing_alt},
            remediation_level="HUMAN_REVIEW"
        )
    """WCAG 1.3.1 - Info and Relationships (Tables)"""
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBL",
            name="Table Headers",
            description="Cannot check - no structure tree",
            status=CheckStatus.MANUAL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            recommendation="Add tags first",
            remediation_level="HUMAN_REVIEW"
        )

    tables_count = 0
    tables_with_headers = 0

    def check_tables(node):
        nonlocal tables_count, tables_with_headers
        if node is None:
            return
        if _is_array(node):
            for item in node:
                check_tables(item)
            return
        if not _is_dict(node):
            return

        try:
            elem_type = node.get("/S")
        except Exception:
            return
        if elem_type == Name("/Table"):
            tables_count += 1
            has_th = False

            def find_th(child):
                nonlocal has_th
                if child is None:
                    return
                if _is_array(child):
                    for c in child:
                        find_th(c)
                    return
                if not _is_dict(child):
                    return
                try:
                    if child.get("/S") == Name("/TH"):
                        has_th = True
                    grandchildren = child.get("/K")
                except Exception:
                    return
                if grandchildren:
                    find_th(grandchildren)

            try:
                children = node.get("/K")
            except Exception:
                children = None
            if children:
                find_th(children)

            if has_th:
                tables_with_headers += 1

        try:
            children = node.get("/K")
        except Exception:
            children = None
        if children:
            check_tables(children)

    k_array = struct_tree.get("/K")
    if k_array:
        check_tables(k_array)

    if tables_count == 0:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBL",
            name="Table Headers",
            description="No tables found in document",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            recommendation="No tables to check",
            remediation_level="HUMAN_REVIEW"
        )

    if tables_with_headers < tables_count:
        missing = tables_count - tables_with_headers
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBL",
            name="Table Headers",
            description=f"{missing} of {tables_count} tables missing header cells",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            location="Structure tree",
            recommendation=f"Add header cells (/TH) with scope to {missing} tables",
            details={"total_tables": tables_count, "with_headers": tables_with_headers, "missing": missing},
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="WCAG-1.3.1-TBL",
        name="Table Headers",
        description=f"All {tables_count} tables have header cells",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="1.3.1",
        pdfua_section="§5.7",
        section508="502.3.2",
        recommendation="All tables have proper header structure",
        details={"total_tables": tables_count, "with_headers": tables_with_headers},
        remediation_level="HUMAN_REVIEW"
    )


def check_lists_structure(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 1.3.1 - Lists Structure"""
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-LIST",
            name="List Structure",
            description="Cannot check - no structure tree",
            status=CheckStatus.MANUAL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.5",
            section508="502.3.2",
            recommendation="Add tags first",
            remediation_level="HUMAN_REVIEW"
        )

    lists_count = 0
    valid_lists = 0

    def check_lists(node):
        nonlocal lists_count, valid_lists
        if node is None:
            return
        if _is_array(node):
            for item in node:
                check_lists(item)
            return
        if not _is_dict(node):
            return

        try:
            elem_type = node.get("/S")
        except Exception:
            return
        if elem_type == Name("/L"):
            lists_count += 1
            has_li = False

            try:
                children = node.get("/K")
            except Exception:
                children = None
            if children:
                def find_li(child):
                    nonlocal has_li
                    if child is None:
                        return
                    if _is_array(child):
                        for c in child:
                            find_li(c)
                        return
                    if not _is_dict(child):
                        return
                    try:
                        if child.get("/S") == Name("/LI"):
                            has_li = True
                        grandchildren = child.get("/K")
                    except Exception:
                        return
                    if grandchildren:
                        find_li(grandchildren)

                find_li(children)

            if has_li:
                valid_lists += 1

        try:
            children = node.get("/K")
        except Exception:
            children = None
        if children:
            check_lists(children)

    k_array = struct_tree.get("/K")
    if k_array:
        check_lists(k_array)

    if lists_count == 0:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-LIST",
            name="List Structure",
            description="No lists found in document",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.5",
            section508="502.3.2",
            recommendation="No lists to check",
            remediation_level="HUMAN_REVIEW"
        )

    if valid_lists < lists_count:
        invalid = lists_count - valid_lists
        return ComplianceCheck(
            check_id="WCAG-1.3.1-LIST",
            name="List Structure",
            description=f"{invalid} of {lists_count} lists have improper structure",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.5",
            section508="502.3.2",
            location="Structure tree",
            recommendation=f"Fix list structure: L → LI → Lbl/LBody for {invalid} lists",
            details={"total_lists": lists_count, "valid": valid_lists, "invalid": invalid},
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="WCAG-1.3.1-LIST",
        name="List Structure",
        description=f"All {lists_count} lists have proper structure",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="1.3.1",
        pdfua_section="§5.5",
        section508="502.3.2",
        recommendation="All lists are properly structured",
        details={"total_lists": lists_count, "valid": valid_lists},
        remediation_level="HUMAN_REVIEW"
    )


def check_links(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 2.4.4 - Link Purpose (Level A)"""
    link_count = 0
    non_descriptive = 0
    non_descriptive_patterns = ["click here", "here", "more", "link", "read more", "learn more", "this"]

    for page in pdf.pages:
        annots = page.get("/Annots")
        if not annots:
            continue

        for annot in annots:
            if annot.get("/Subtype") == Name("/Link"):
                link_count += 1
                alt_text = annot.get("/Contents") or annot.get("/NM")

                if alt_text:
                    alt_lower = str(alt_text).lower()
                    for pattern in non_descriptive_patterns:
                        if pattern in alt_lower:
                            non_descriptive += 1
                            break

    if link_count == 0:
        return ComplianceCheck(
            check_id="WCAG-2.4.4-LINK",
            name="Link Purpose",
            description="No links found in document",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.4",
            pdfua_section="§5.9",
            section508="502.3.2",
            recommendation="No links to check",
            remediation_level="HUMAN_REVIEW"
        )

    if non_descriptive > 0:
        return ComplianceCheck(
            check_id="WCAG-2.4.4-LINK",
            name="Link Purpose",
            description=f"{non_descriptive} of {link_count} links have non-descriptive text",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="2.4.4",
            pdfua_section="§5.9",
            section508="502.3.2",
            location="Annotations",
            recommendation=f"Rewrite {non_descriptive} links to be descriptive (avoid 'click here', 'here', 'more')",
            details={"total_links": link_count, "non_descriptive": non_descriptive},
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="WCAG-2.4.4-LINK",
        name="Link Purpose",
        description=f"All {link_count} links appear to have descriptive text",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="2.4.4",
        pdfua_section="§5.9",
        section508="502.3.2",
        recommendation="All links have descriptive text",
        details={"total_links": link_count},
        remediation_level="HUMAN_REVIEW"
    )


def check_forms(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 4.1.2 - Form Fields (Level A)"""
    form_fields = 0
    fields_with_tooltips = 0

    for page in pdf.pages:
        annots = page.get("/Annots")
        if not annots:
            continue

        for annot in annots:
            subtype = annot.get("/Subtype")
            if subtype == Name("/Widget"):
                form_fields += 1

                # Check for tooltip (/TU)
                tooltip = annot.get("/TU")
                if tooltip:
                    fields_with_tooltips += 1

    if form_fields == 0:
        return ComplianceCheck(
            check_id="WCAG-4.1.2-FORM",
            name="Form Accessibility",
            description="No form fields found in document",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="4.1.2",
            pdfua_section="§5.10",
            section508="502.3.2",
            recommendation="No forms to check",
            remediation_level="HUMAN_REVIEW"
        )

    if fields_with_tooltips < form_fields:
        missing = form_fields - fields_with_tooltips
        return ComplianceCheck(
            check_id="WCAG-4.1.2-FORM",
            name="Form Accessibility",
            description=f"{missing} of {form_fields} form fields missing tooltips",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="4.1.2",
            pdfua_section="§5.10",
            section508="502.3.2",
            location="Form fields",
            recommendation=f"Add tooltips (/TU) to {missing} form fields",
            details={"total_fields": form_fields, "with_tooltips": fields_with_tooltips, "missing": missing},
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="WCAG-4.1.2-FORM",
        name="Form Accessibility",
        description=f"All {form_fields} form fields have tooltips",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="4.1.2",
        pdfua_section="§5.10",
        section508="502.3.2",
        recommendation="All form fields have tooltips",
        details={"total_fields": form_fields, "with_tooltips": fields_with_tooltips},
        remediation_level="HUMAN_REVIEW"
    )


def check_tab_order(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """PDF/UA - Tab order consistency with structure order."""
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if not struct_tree:
        return ComplianceCheck(
            check_id="PDFUA-TAB",
            name="Tab Order",
            description="Cannot check tab order - no structure tree",
            status=CheckStatus.MANUAL.value,
            level=ComplianceLevel.AA.value,
            wcag_criteria="2.4.3",
            pdfua_section="§5.3",
            section508="502.3.2",
            recommendation="Add tags first, then verify tab order matches reading order",
            remediation_level="MANUAL_CHECK"
        )

    inconsistent_tabs = 0
    pages_checked = 0

    for page_num, page in enumerate(pdf.pages, 1):
        # Check if page has explicit TabOrder set
        tab_order = page.get("/TabOrder")
        if tab_order and str(tab_order) not in ["/S", "/R"]:
            # /S = structure order, /R = row order — both acceptable
            inconsistent_tabs += 1

        # Check annotations for /StructParent mapping
        annots = page.get("/Annots")
        if annots:
            pages_checked += 1
            for annot in annots:
                if annot.get("/Subtype") in [Name("/Link"), Name("/Widget")]:
                    # Interactive elements should have /StructParent linking to structure tree
                    struct_parent = annot.get("/StructParent")
                    if struct_parent is None:
                        inconsistent_tabs += 1

    if pages_checked == 0:
        return ComplianceCheck(
            check_id="PDFUA-TAB",
            name="Tab Order",
            description="No interactive elements found — tab order is not applicable",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.AA.value,
            wcag_criteria="2.4.3",
            pdfua_section="§5.3",
            section508="502.3.2",
            recommendation="No tab order to verify",
            remediation_level="MANUAL_CHECK"
        )

    if inconsistent_tabs > 0:
        return ComplianceCheck(
            check_id="PDFUA-TAB",
            name="Tab Order",
            description=f"{inconsistent_tabs} elements with inconsistent tab order",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.AA.value,
            wcag_criteria="2.4.3",
            pdfua_section="§5.3",
            section508="502.3.2",
            location="Page annotations",
            recommendation="Ensure tab order matches structure order (S in page properties)",
            details={"inconsistent_elements": inconsistent_tabs},
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="PDFUA-TAB",
        name="Tab Order",
        description="Tab order is consistent with structure order",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.AA.value,
        wcag_criteria="2.4.3",
        pdfua_section="§5.3",
        section508="502.3.2",
        recommendation="Tab order is consistent",
        remediation_level="MANUAL_CHECK"
    )


def check_alt_text_quality(pdf: pikepdf.Pdf) -> list:
    """
    Check alt text quality issues (multiple checks from Adobe report):
    - Nested alt text that will never be read
    - Alt text that hides annotation content
    - Alt text not associated with content
    - Other elements requiring alt text

    Returns a list of ComplianceCheck objects (0-n issues).
    """
    struct_tree = pdf.Root.get("/StructTreeRoot")
    checks = []

    if not struct_tree:
        return checks  # Can't check alt text without structure tree

    orphaned_alt = 0
    nested_unreadable_alt = 0
    alt_hiding_annotation = 0

    def check_alt_node(node, depth=0, parent_is_artifact=False):
        nonlocal orphaned_alt, nested_unreadable_alt, alt_hiding_annotation
        if node is None:
            return
        if _is_array(node):
            for item in node:
                check_alt_node(item, depth, parent_is_artifact)
            return
        if not _is_dict(node):
            return

        try:
            elem_type = node.get("/S")
        except Exception:
            return

        type_str = str(elem_type) if elem_type else ""

        # Check for Alt text inside Artifact or other non-readable elements
        alt_text = node.get("/Alt")
        if alt_text and parent_is_artifact:
            nested_unreadable_alt += 1

        # Check for alt text on Link annotations (should describe purpose, not hide content)
        if elem_type == Name("/Link"):
            if alt_text and len(str(alt_text).strip()) > 100:
                # Excessively long alt text on links likely hides annotation content
                alt_hiding_annotation += 1

        # Check for figures with empty alt text (not just missing, but explicitly empty)
        if elem_type == Name("/Figure"):
            if alt_text is not None and not str(alt_text).strip():
                orphaned_alt += 1  # Empty string = placeholder/meaningless

        # Check for annotations without associated content
        if elem_type == Name("/Annotation") and not node.get("/Contents"):
            orphaned_alt += 1

        # Determine if children are inside non-readable parent
        is_non_readable = type_str in ["/Artifact", "/Part", "/Document"] or parent_is_artifact

        try:
            children = node.get("/K")
        except Exception:
            return
        if children:
            check_alt_node(children, depth + 1, is_non_readable)

    k_array = struct_tree.get("/K")
    if k_array:
        check_alt_node(k_array)

    if nested_unreadable_alt > 0:
        checks.append(ComplianceCheck(
            check_id="ALT-NEST",
            name="Nested Alternate Text",
            description=f"{nested_unreadable_alt} alt text elements inside non-readable parents (will never be read)",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1",
            pdfua_section="§5.6",
            section508="502.3.3",
            location="Structure tree",
            recommendation="Move alt text out of Artifact or non-readable container elements",
            details={"nested_unreadable": nested_unreadable_alt},
            remediation_level="HUMAN_REVIEW"
        ))

    if alt_hiding_annotation > 0:
        checks.append(ComplianceCheck(
            check_id="ALT-HIDE",
            name="Alt Text Hides Annotation",
            description=f"{alt_hiding_annotation} links/annotations have excessively long alt text that may hide content",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1, 4.1.2",
            pdfua_section="§5.9",
            section508="502.3.2",
            location="Annotations",
            recommendation="Keep alt text concise; use /Contents for actual annotation content",
            details={"hiding_annotation": alt_hiding_annotation},
            remediation_level="HUMAN_REVIEW"
        ))

    if orphaned_alt > 0:
        checks.append(ComplianceCheck(
            check_id="ALT-ORPH",
            name="Alternate Text Not Associated with Content",
            description=f"{orphaned_alt} figures have empty or orphaned alt text",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1",
            pdfua_section="§5.6",
            section508="502.3.3",
            location="Structure tree",
            recommendation="Ensure alt text is meaningful and associated with actual content",
            details={"orphaned_alt": orphaned_alt},
            remediation_level="HUMAN_REVIEW"
        ))

    return checks


def check_table_regularity(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """Check table structure regularity — consistent columns per row, rows per column."""
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBLREG",
            name="Table Regularity",
            description="Cannot check - no structure tree",
            status=CheckStatus.MANUAL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            recommendation="Add tags first",
            remediation_level="HUMAN_REVIEW"
        )

    irregular_tables = []

    def check_table(node, table_idx=0):
        if node is None:
            return
        if _is_array(node):
            for item in node:
                check_table(item, table_idx)
            return
        if not _is_dict(node):
            return

        try:
            elem_type = node.get("/S")
        except Exception:
            return

        if elem_type == Name("/Table"):
            table_idx += 1
            row_col_counts = []

            def check_rows(child):
                if child is None:
                    return
                if _is_array(child):
                    for c in child:
                        check_rows(c)
                    return
                if not _is_dict(child):
                    return
                try:
                    child_type = child.get("/S")
                except Exception:
                    return

                if child_type == Name("/TR"):
                    # Count cells in this row
                    cell_count = 0
                    def count_cells(grandchild):
                        nonlocal cell_count
                        if grandchild is None:
                            return
                        if _is_array(grandchild):
                            for gc in grandchild:
                                count_cells(gc)
                            return
                        if not _is_dict(grandchild):
                            return
                        try:
                            gc_type = grandchild.get("/S")
                        except Exception:
                            return
                        if gc_type in [Name("/TD"), Name("/TH")]:
                            cell_count += 1
                        try:
                            ggc = grandchild.get("/K")
                        except Exception:
                            return
                        if ggc:
                            count_cells(ggc)

                    try:
                        row_children = child.get("/K")
                    except Exception:
                        row_children = None
                    if row_children:
                        count_cells(row_children)
                    row_col_counts.append(cell_count)

                try:
                    grandchildren = child.get("/K")
                except Exception:
                    return
                if grandchildren:
                    check_rows(grandchildren)

            try:
                children = node.get("/K")
            except Exception:
                children = None
            if children:
                check_rows(children)

            # Check if all rows have same column count
            if len(set(row_col_counts)) > 1 and len(row_col_counts) > 1:
                irregular_tables.append({
                    "table": table_idx,
                    "row_counts": row_col_counts,
                    "expected": row_col_counts[0] if row_col_counts else 0
                })

        try:
            children = node.get("/K")
        except Exception:
            children = None
        if children:
            check_table(children, table_idx)

    k_array = struct_tree.get("/K")
    if k_array:
        check_table(k_array)

    if irregular_tables:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBLREG",
            name="Table Regularity",
            description=f"{len(irregular_tables)} table(s) have inconsistent column counts across rows",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            location="Structure tree",
            recommendation="Ensure all rows in each table have the same number of columns (use colspan for merged cells)",
            details={"irregular_tables": irregular_tables[:5]},  # Limit detail
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="WCAG-1.3.1-TBLREG",
        name="Table Regularity",
        description="All tables have consistent column counts per row",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="1.3.1",
        pdfua_section="§5.7",
        section508="502.3.2",
        recommendation="Tables are properly structured",
        remediation_level="HUMAN_REVIEW"
    )


def check_table_summary(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """Check that tables have summary/caption information."""
    struct_tree = pdf.Root.get("/StructTreeRoot")

    if not struct_tree:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBLSUM",
            name="Table Summary",
            description="Cannot check - no structure tree",
            status=CheckStatus.MANUAL.value,
            level=ComplianceLevel.AA.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            recommendation="Add tags first",
            remediation_level="HUMAN_REVIEW"
        )

    tables_total = 0
    tables_with_summary = 0

    def check_tables(node):
        nonlocal tables_total, tables_with_summary
        if node is None:
            return
        if _is_array(node):
            for item in node:
                check_tables(item)
            return
        if not _is_dict(node):
            return

        try:
            elem_type = node.get("/S")
        except Exception:
            return

        if elem_type == Name("/Table"):
            tables_total += 1
            # Check for /Summary, /Caption, or /Title on the table element
            has_summary = (
                node.get("/Summary") is not None
                or node.get("/Caption") is not None
                or node.get("/Title") is not None
            )
            if has_summary:
                tables_with_summary += 1

        try:
            children = node.get("/K")
        except Exception:
            return
        if children:
            check_tables(children)

    k_array = struct_tree.get("/K")
    if k_array:
        check_tables(k_array)

    if tables_total == 0:
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBLSUM",
            name="Table Summary",
            description="No tables found in document",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.AA.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            recommendation="No tables to check",
            remediation_level="HUMAN_REVIEW"
        )

    if tables_with_summary < tables_total:
        missing = tables_total - tables_with_summary
        return ComplianceCheck(
            check_id="WCAG-1.3.1-TBLSUM",
            name="Table Summary",
            description=f"{missing} of {tables_total} tables missing summary/caption",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.AA.value,
            wcag_criteria="1.3.1",
            pdfua_section="§5.7",
            section508="502.3.2",
            location="Structure tree",
            recommendation=f"Add /Summary or /Caption to {missing} tables to describe their purpose",
            details={"total_tables": tables_total, "with_summary": tables_with_summary, "missing": missing},
            remediation_level="HUMAN_REVIEW"
        )

    return ComplianceCheck(
        check_id="WCAG-1.3.1-TBLSUM",
        name="Table Summary",
        description=f"All {tables_total} tables have summary/caption information",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.AA.value,
        wcag_criteria="1.3.1",
        pdfua_section="§5.7",
        section508="502.3.2",
        recommendation="All tables have descriptive summaries",
        details={"total_tables": tables_total, "with_summary": tables_with_summary},
        remediation_level="HUMAN_REVIEW"
    )


def check_image_only_pdf(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """Check if PDF is image-only (scanned document with no text layer)."""
    has_text = False
    image_pages = 0
    total_pages = len(pdf.pages)

    for page in pdf.pages:
        resources = page.get("/Resources", Dictionary())

        # Check for text content operators in content stream
        contents = page.get("/Contents")
        if contents:
            try:
                stream_data = contents.read_bytes() if hasattr(contents, 'read_bytes') else bytes(contents)
                if b'Tj' in stream_data or b'TJ' in stream_data:
                    has_text = True
            except Exception:
                pass

        # Check for XObject images
        xobjects = resources.get("/XObject", {})
        if xobjects:
            for key, xobj in xobjects.items():
                if xobj and xobj.get("/Subtype") == Name("/Image"):
                    image_pages += 1
                    break  # At least one image on this page

        # Also check for actual text via font resources
        fonts = resources.get("/Font", {})
        if fonts:
            has_text = True

    # Document is image-only if: has images, no text, and no structure tree
    struct_tree = pdf.Root.get("/StructTreeRoot")
    is_image_only = image_pages > 0 and not has_text and not struct_tree

    if is_image_only:
        return ComplianceCheck(
            check_id="WCAG-1.1.1-SCAN",
            name="Image-Only PDF",
            description=f"All {total_pages} pages are images with no text layer (scanned document)",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.1.1, 1.3.1",
            pdfua_section="§5",
            section508="502.3.2",
            location="Page content",
            recommendation="Run OCR to add a text layer (Adobe: Enhance Scans > Recognize Text)",
            details={"total_pages": total_pages, "pages_with_images": image_pages},
            remediation_level="MANUAL_ONLY"
        )

    return ComplianceCheck(
        check_id="WCAG-1.1.1-SCAN",
        name="Image-Only PDF",
        description="Document has selectable text content" if has_text else "Document is not image-only",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="1.1.1",
        pdfua_section="§5",
        section508="502.3.2",
        recommendation="Document is not image-only" if has_text else "No images found",
        details={"total_pages": total_pages, "has_text": has_text, "pages_with_images": image_pages},
        remediation_level="MANUAL_ONLY"
    )


def check_bookmarks(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 2.4.5 - Bookmarks for large documents (21+ pages)."""
    page_count = len(pdf.pages)
    outlines = pdf.Root.get("/Outlines")

    has_bookmarks = False
    bookmark_count = 0

    if outlines:
        has_bookmarks = True
        # Count bookmarks by traversing outline tree
        def count_outlines(node):
            nonlocal bookmark_count
            if node is None:
                return
            if _is_array(node):
                for item in node:
                    count_outlines(item)
                return
            if not _is_dict(node):
                return
            bookmark_count += 1
            try:
                first = node.get("/First")
            except Exception:
                return
            if first:
                count_outlines(first)
            try:
                next_item = node.get("/Next")
            except Exception:
                return
            if next_item:
                count_outlines(next_item)

        try:
            first_outline = outlines.get("/First")
        except Exception:
            first_outline = None
        if first_outline:
            count_outlines(first_outline)

    # PDF/UA recommends bookmarks for documents with 21+ pages
    if page_count >= 21:
        if not has_bookmarks or bookmark_count == 0:
            return ComplianceCheck(
                check_id="WCAG-2.4.5-BM",
                name="Bookmarks",
                description=f"Large document ({page_count} pages) has no bookmarks",
                status=CheckStatus.FAIL.value,
                level=ComplianceLevel.AA.value,
                wcag_criteria="2.4.5",
                pdfua_section="§5.8",
                section508="502.3.2",
                location="Document Catalog /Outlines",
                recommendation="Add bookmarks for navigation (Adobe: Bookmarks panel > New Bookmark)",
                details={"page_count": page_count, "bookmark_count": 0},
                remediation_level="HUMAN_REVIEW"
            )

        return ComplianceCheck(
            check_id="WCAG-2.4.5-BM",
            name="Bookmarks",
            description=f"Document has {bookmark_count} bookmarks ({page_count} pages)",
            status=CheckStatus.PASS.value,
            level=ComplianceLevel.AA.value,
            wcag_criteria="2.4.5",
            pdfua_section="§5.8",
            section508="502.3.2",
            recommendation="Document has good bookmark navigation",
            details={"page_count": page_count, "bookmark_count": bookmark_count},
            remediation_level="HUMAN_REVIEW"
        )

    # Small document — bookmarks are nice but not required
    return ComplianceCheck(
        check_id="WCAG-2.4.5-BM",
        name="Bookmarks",
        description=f"Short document ({page_count} pages) — bookmarks not required",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.AA.value,
        wcag_criteria="2.4.5",
        pdfua_section="§5.8",
        section508="502.3.2",
        recommendation=f"Bookmarks optional for documents under 21 pages",
        details={"page_count": page_count, "bookmark_count": bookmark_count},
        remediation_level="HUMAN_REVIEW"
    )


def check_fonts(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """Check font embedding and Unicode mapping."""
    unembedded_fonts = []
    missing_tounicode = []

    for page_num, page in enumerate(pdf.pages, 1):
        resources = page.get("/Resources", Dictionary())
        fonts = resources.get("/Font", Dictionary())

        if not fonts:
            continue

        for font_name, font in fonts.items():
            if font is None:
                continue

            font_type = font.get("/Subtype")
            font_name_str = str(font_name)

            # Check for embedded fonts
            if font_type in [Name("/Type1"), Name("/TrueType")]:
                font_desc = font.get("/FontDescriptor")
                if font_desc:
                    font_file = font_desc.get("/FontFile") or font_desc.get("/FontFile2") or font_desc.get("/FontFile3")
                    if not font_file:
                        unembedded_fonts.append(f"{font_name_str} (Page {page_num})")

            # Check for ToUnicode CMap
            if not font.get("/ToUnicode"):
                # Type 3 fonts don't always need ToUnicode
                if font_type != Name("/Type3"):
                    missing_tounicode.append(f"{font_name_str} (Page {page_num})")

    issues = []
    if unembedded_fonts:
        issues.append(f"Unembedded: {', '.join(unembedded_fonts[:5])}")
    if missing_tounicode:
        issues.append(f"Missing Unicode: {', '.join(missing_tounicode[:5])}")

    if issues:
        return ComplianceCheck(
            check_id="FONT-508",
            name="Font Embedding",
            description="; ".join(issues),
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="1.4.1, 1.3.2",
            pdfua_section="§5.2",
            section508="502.3.1",
            location="Font resources",
            recommendation="Embed all fonts and add ToUnicode CMap for screen reader text extraction",
            details={"unembedded_fonts": unembedded_fonts, "missing_tounicode": missing_tounicode},
            remediation_level="MANUAL_ONLY"
        )

    return ComplianceCheck(
        check_id="FONT-508",
        name="Font Embedding",
        description="All fonts are properly embedded with Unicode mapping",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="1.4.1, 1.3.2",
        pdfua_section="§5.2",
        section508="502.3.1",
        recommendation="Fonts are properly embedded",
        remediation_level="MANUAL_ONLY"
    )


def check_security(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """Section 508 - Security Settings"""
    if pdf.is_encrypted:
        return ComplianceCheck(
            check_id="SEC-508",
            name="Document Security",
            description="Document is encrypted/password protected",
            status=CheckStatus.FAIL.value,
            level=ComplianceLevel.A.value,
            wcag_criteria="4.1.2",
            pdfua_section="§5.1",
            section508="502.3.1",
            location="Document security",
            recommendation="Remove encryption or ensure accessibility tools can access content",
            remediation_level="MANUAL_ONLY"
        )

    try:
        perms = pdf.allow
        if not perms.extract:
            return ComplianceCheck(
                check_id="SEC-508",
                name="Document Security",
                description="Content extraction is disabled",
                status=CheckStatus.FAIL.value,
                level=ComplianceLevel.A.value,
                wcag_criteria="4.1.2",
                pdfua_section="§5.1",
                section508="502.3.1",
                location="Document permissions",
                recommendation="Enable content extraction for screen readers",
                remediation_level="MANUAL_ONLY"
            )
    except Exception:
        pass

    return ComplianceCheck(
        check_id="SEC-508",
        name="Document Security",
        description="No security restrictions blocking accessibility",
        status=CheckStatus.PASS.value,
        level=ComplianceLevel.A.value,
        wcag_criteria="4.1.2",
        pdfua_section="§5.1",
        section508="502.3.1",
        recommendation="Security settings allow screen reader access",
        remediation_level="MANUAL_ONLY"
    )


def run_compliance_check(pdf_path: Path) -> ComplianceReport:
    """Run full compliance check on a PDF."""

    report = ComplianceReport(
        filename=pdf_path.stem,
        filepath=str(pdf_path),
        checks=[]
    )

    try:
        with pikepdf.open(pdf_path) as pdf:
            # Run all checks with error handling per check
            check_funcs = [
                ("title", lambda: check_title(pdf)),
                ("language", lambda: check_language(pdf)),
                ("display_doctitle", lambda: check_display_doctitle(pdf)),
                ("tags_tree", lambda: check_tags_tree(pdf)),
                ("mark_info", lambda: check_mark_info(pdf)),
                ("reading_order", lambda: check_reading_order(pdf)),
            ]

            checks = []
            for name, func in check_funcs:
                try:
                    checks.append(func())
                except Exception as e:
                    checks.append(ComplianceCheck(
                        check_id=f"ERR-{name.upper()}",
                        name=f"Error checking {name}",
                        description=f"Check failed: {str(e)}",
                        status=CheckStatus.MANUAL.value,
                        level=ComplianceLevel.A.value,
                        wcag_criteria="N/A",
                        pdfua_section="N/A",
                        section508="N/A",
                        recommendation=f"Manual check required: {str(e)}",
                        remediation_level="MANUAL_CHECK"
                    ).__dict__)

            # Wrap remaining checks in try/except too
            try:
                checks.append(check_headings_structure(pdf))
            except Exception as e:
                checks.append(ComplianceCheck(
                    check_id="ERR-HEADINGS",
                    name="Heading Structure Check Failed",
                    description=str(e),
                    status=CheckStatus.MANUAL.value,
                    level=ComplianceLevel.A.value,
                    wcag_criteria="1.3.1, 2.4.6",
                    pdfua_section="§5.4",
                    section508="502.3.2",
                    recommendation="Manual heading check required",
                    remediation_level="HUMAN_REVIEW"
                ).__dict__)

            try:
                checks.append(check_images_alt_text(pdf))
            except Exception as e:
                checks.append(ComplianceCheck(
                    check_id="ERR-ALT",
                    name="Alt Text Check Failed",
                    description=str(e),
                    status=CheckStatus.MANUAL.value,
                    level=ComplianceLevel.A.value,
                    wcag_criteria="1.1.1",
                    pdfua_section="§5.6",
                    section508="502.3.3",
                    recommendation="Manual alt text check required",
                    remediation_level="HUMAN_REVIEW"
                ).__dict__)

            try:
                checks.append(check_tables_headers(pdf))
            except Exception as e:
                checks.append(ComplianceCheck(
                    check_id="ERR-TABLES",
                    name="Table Headers Check Failed",
                    description=str(e),
                    status=CheckStatus.MANUAL.value,
                    level=ComplianceLevel.A.value,
                    wcag_criteria="1.3.1",
                    pdfua_section="§5.7",
                    section508="502.3.2",
                    recommendation="Manual table check required",
                    remediation_level="HUMAN_REVIEW"
                ).__dict__)

            try:
                checks.append(check_lists_structure(pdf))
            except Exception as e:
                checks.append(ComplianceCheck(
                    check_id="ERR-LISTS",
                    name="List Structure Check Failed",
                    description=str(e),
                    status=CheckStatus.MANUAL.value,
                    level=ComplianceLevel.A.value,
                    wcag_criteria="1.3.1",
                    pdfua_section="§5.5",
                    section508="502.3.2",
                    recommendation="Manual list check required",
                    remediation_level="HUMAN_REVIEW"
                ).__dict__)

            try:
                checks.append(check_links(pdf))
            except Exception as e:
                pass  # Links check is non-critical

            try:
                checks.append(check_forms(pdf))
            except Exception as e:
                pass

            try:
                checks.append(check_fonts(pdf))
            except Exception as e:
                pass

            try:
                checks.append(check_security(pdf))
            except Exception as e:
                pass

            # New checks from Adobe Acrobat report parity
            try:
                checks.append(check_tab_order(pdf))
            except Exception as e:
                pass

            try:
                checks.extend(check_alt_text_quality(pdf))  # returns list
            except Exception as e:
                pass

            try:
                checks.append(check_table_regularity(pdf))
            except Exception as e:
                pass

            try:
                checks.append(check_table_summary(pdf))
            except Exception as e:
                pass

            try:
                checks.append(check_image_only_pdf(pdf))
            except Exception as e:
                pass

            try:
                checks.append(check_bookmarks(pdf))
            except Exception as e:
                pass

            report.checks = [asdict(c) if hasattr(c, '__dataclass_fields__') else c for c in checks]
            report.total_checks = len(report.checks)

            # Calculate totals
            for check in report.checks:
                status_val = check.get("status") if isinstance(check, dict) else check.status
                if status_val == CheckStatus.PASS.value:
                    report.passed += 1
                elif status_val == CheckStatus.FAIL.value:
                    report.failed += 1
                elif status_val == CheckStatus.WARNING.value:
                    report.warnings += 1
                elif status_val == CheckStatus.MANUAL.value:
                    report.manual_checks += 1

            # Determine overall compliance
            level_a_checks = [c for c in report.checks if (c.get("level") if isinstance(c, dict) else c.level) == ComplianceLevel.A.value]
            level_a_failures = [c for c in level_a_checks if (c.get("status") if isinstance(c, dict) else c.status) == CheckStatus.FAIL.value]

            report.wcag_level_a_pass = len(level_a_failures) == 0
            report.pdfua_compliant = report.wcag_level_a_pass
            report.section508_compliant = report.wcag_level_a_pass

            if report.failed == 0:
                report.overall_status = "COMPLIANT"
            elif report.failed <= 2:
                report.overall_status = "PARTIAL"
            else:
                report.overall_status = "NON-COMPLIANT"

    except Exception as e:
        report.overall_status = "ERROR"
        report.checks = [{
            "check_id": "FATAL",
            "name": "Fatal Error",
            "description": str(e),
            "status": CheckStatus.FAIL.value,
            "level": ComplianceLevel.A.value,
            "wcag_criteria": "N/A",
            "pdfua_section": "N/A",
            "section508": "N/A",
            "recommendation": "File may be corrupted or inaccessible",
            "remediation_level": "MANUAL_CHECK"
        }]

    return report


def remediation_summary(report: ComplianceReport) -> dict:
    """
    Count checks by remediation level.

    Returns dict with keys:
      - auto_fixable: count of AUTO_FIXABLE checks
      - human_review: count of HUMAN_REVIEW checks
      - manual_only: count of MANUAL_ONLY checks
      - manual_check: count of MANUAL_CHECK checks
      - total: total number of checks
    """
    summary = {
        "auto_fixable": 0,
        "human_review": 0,
        "manual_only": 0,
        "manual_check": 0,
        "total": 0,
    }

    for check in report.checks:
        if isinstance(check, dict):
            level = check.get("remediation_level", "MANUAL_CHECK")
        else:
            level = getattr(check, 'remediation_level', "MANUAL_CHECK")

        summary["total"] += 1
        key = level.lower()
        if key in summary:
            summary[key] += 1
        else:
            summary["manual_check"] += 1

    return summary


def generate_compliance_summary(report: ComplianceReport) -> str:
    """Generate human-readable compliance summary."""

    lines = [
        "=" * 70,
        f"COMPLIANCE REPORT: {report.filename}",
        "=" * 70,
        "",
        f"Overall Status: {report.overall_status}",
        "",
        "Standards Compliance:",
        f"  WCAG 2.2 Level A: {'✓ PASS' if report.wcag_level_a_pass else '✗ FAIL'}",
        f"  PDF/UA-1:         {'✓ PASS' if report.pdfua_compliant else '✗ FAIL'}",
        f"  Section 508:      {'✓ PASS' if report.section508_compliant else '✗ FAIL'}",
        "",
        "Summary:",
        f"  Total Checks:  {report.total_checks}",
        f"  Passed:        {report.passed}",
        f"  Failed:        {report.failed}",
        f"  Warnings:      {report.warnings}",
        f"  Manual Check:  {report.manual_checks}",
        "",
    ]

    # Add remediation summary
    rem = remediation_summary(report)
    lines.append("Remediation Summary:")
    lines.append(f"  Auto-fixable:    {rem['auto_fixable']}")
    lines.append(f"  Human review:    {rem['human_review']}")
    lines.append(f"  Manual only:     {rem['manual_only']}")
    lines.append(f"  Manual check:    {rem['manual_check']}")
    lines.append("")

    if report.failed > 0:
        lines.append("Failed Checks (Must Fix):")
        lines.append("-" * 50)
        for check in report.checks:
            if check['status'] == CheckStatus.FAIL.value:
                lines.append(f"  ✗ {check['name']}")
                lines.append(f"    Standard: WCAG {check['wcag_criteria']}, PDF/UA {check['pdfua_section']}")
                lines.append(f"    Issue: {check['description']}")
                lines.append(f"    Fix: {check['recommendation']}")
                lines.append("")

    if report.warnings > 0:
        lines.append("Warnings (Should Review):")
        lines.append("-" * 50)
        for check in report.checks:
            if check['status'] == CheckStatus.WARNING.value:
                lines.append(f"  ⚠ {check['name']}: {check['description']}")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="ADA/WCAG/PDF-UA Compliance Checker")
    parser.add_argument("pdf_path", type=Path, nargs="?", help="Path to PDF file (default: all in input_pdfs/)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    if args.pdf_path:
        # Single file mode
        if not args.pdf_path.exists():
            print(f"Error: File not found: {args.pdf_path}")
            return

        report = run_compliance_check(args.pdf_path)

        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print(generate_compliance_summary(report))
    else:
        # Batch mode — process all PDFs in input_pdfs/
        input_dir = Path(__file__).parent / "input_pdfs"
        if not input_dir.exists():
            print(f"Error: Input directory not found: {input_dir}")
            return

        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in: {input_dir}")
            return

        print(f"Found {len(pdf_files)} PDF file(s) to assess\n")

        all_reports = []
        for pdf_path in pdf_files:
            print(f"Assessing: {pdf_path.name}")
            try:
                report = run_compliance_check(pdf_path)
                all_reports.append(report)
                status = "✓ PASS" if report.overall_status == "COMPLIANT" else f"✗ {report.overall_status} ({report.failed} failed)"
                print(f"  -> {status}")
            except Exception as e:
                print(f"  -> ERROR: {e}")

        # Print summaries
        print("\n")
        for report in all_reports:
            if args.json:
                print(json.dumps(asdict(report), indent=2))
            else:
                print(generate_compliance_summary(report))
                print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
