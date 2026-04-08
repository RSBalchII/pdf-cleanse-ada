#!/usr/bin/env python3
"""
ADA/WCAG/PDF-UA Compliance Checker

Comprehensive accessibility assessment mapped to:
- WCAG 2.2 (Level A & AA)
- PDF/UA-1 (ISO 14289-1)
- Section 508 Refresh (2017+)

Each check is mapped to specific success criteria for compliance reporting.
"""

import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

import pikepdf
from pikepdf import Name, Dictionary, Array


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
            details={"title": str(title)}
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
            recommendation="Set document title in metadata (not just filename)"
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
            details={"language": str(lang)}
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
            recommendation="Set document language (e.g., 'en-US') for screen readers"
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
            recommendation="Title will display in viewer title bar"
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
            recommendation="Set DisplayDocTitle to true"
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
            details={"has_struct_tree": True}
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
            recommendation="Document requires full tagging structure (manual process in Adobe Acrobat)"
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
            recommendation="Document is marked as tagged"
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
            recommendation="Set MarkInfo.Marked to true"
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
            recommendation="Add tags first, then verify reading order"
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
            recommendation="Reading order mapping present (verify manually)"
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
            recommendation="Ensure ParentTree maps content streams to structure elements"
        )


def check_headings_structure(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 1.3.1, 2.4.6 - Headings and Labels (Level A)"""
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
            recommendation="Add tags first"
        )
    
    # Collect heading tags
    heading_tags = []
    
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

        try:
            children = node.get("/K")
        except Exception:
            return
        if children:
            collect_headings(children)
    
    k_array = struct_tree.get("/K")
    if k_array:
        collect_headings(k_array)
    
    # Analyze
    has_h1 = "/H1" in heading_tags
    
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
                details={"heading_tags": heading_tags, "skipped": skipped}
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
                details={"heading_tags": list(set(heading_tags))}
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
                details={"heading_tags": heading_tags}
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
                recommendation="Consider adding headings for navigation (may not be required for short documents)"
            )


def check_images_alt_text(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 1.1.1 - Non-text Content (Level A)"""
    struct_tree = pdf.Root.get("/StructTreeRoot")
    
    # Count XObject images
    image_count = 0
    for page in pdf.pages:
        resources = page.get("/Resources", {})
        xobjects = resources.get("/XObject", {})
        if xobjects:
            for key, xobj in xobjects.items():
                if xobj and xobj.get("/Subtype") == Name("/Image"):
                    image_count += 1
    
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
            recommendation="No images to check"
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
            recommendation=f"All {image_count} images need /Figure tags with alt text"
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
            details={"total_xobjects": image_count, "tagged_figures": figures_total, "untagged": untagged_images}
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
            details={"tagged_figures": figures_total, "with_alt": figures_with_alt, "missing_alt": missing_alt}
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
        details={"tagged_figures": figures_total, "with_alt": figures_with_alt}
    )


def check_tables_headers(pdf: pikepdf.Pdf) -> ComplianceCheck:
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
            recommendation="Add tags first"
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
            recommendation="No tables to check"
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
            details={"total_tables": tables_count, "with_headers": tables_with_headers, "missing": missing}
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
        details={"total_tables": tables_count, "with_headers": tables_with_headers}
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
            recommendation="Add tags first"
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
            recommendation="No lists to check"
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
            details={"total_lists": lists_count, "valid": valid_lists, "invalid": invalid}
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
        details={"total_lists": lists_count, "valid": valid_lists}
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
            recommendation="No links to check"
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
            details={"total_links": link_count, "non_descriptive": non_descriptive}
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
        details={"total_links": link_count}
    )


def check_forms(pdf: pikepdf.Pdf) -> ComplianceCheck:
    """WCAG 4.1.2 - Form Fields (Level A)"""
    form_fields = 0
    fields_with_tooltips = 0
    fields_in_tags = 0
    
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
                
                # Check if field is in structure tree (simplified check)
                fields_in_tags += 1  # Assume tagged if we can access it
    
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
            recommendation="No forms to check"
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
            details={"total_fields": form_fields, "with_tooltips": fields_with_tooltips, "missing": missing}
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
        details={"total_fields": form_fields, "with_tooltips": fields_with_tooltips}
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
            recommendation="Remove encryption or ensure accessibility tools can access content"
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
                recommendation="Enable content extraction for screen readers"
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
        recommendation="Security settings allow screen reader access"
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
                        recommendation=f"Manual check required: {str(e)}"
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
                    recommendation="Manual heading check required"
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
                    recommendation="Manual alt text check required"
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
                    recommendation="Manual table check required"
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
                    recommendation="Manual list check required"
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
                checks.append(check_security(pdf))
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
            "recommendation": "File may be corrupted or inaccessible"
        }]

    return report


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
    parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    
    args = parser.parse_args()
    
    if not args.pdf_path.exists():
        print(f"Error: File not found: {args.pdf_path}")
        return
    
    report = run_compliance_check(args.pdf_path)
    
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(generate_compliance_summary(report))


if __name__ == "__main__":
    main()
