#!/usr/bin/env python3
"""
ADA Accessibility Assessment Tool for PDFs

Analyzes PDFs for WCAG 2.1 AA / PDF/UA-1 / Section 508 compliance issues.
Categorizes findings by remediation level:
  - AUTO_FIXABLE: Can be fixed programmatically
  - HUMAN_REVIEW: Detectable but requires human judgment
  - MANUAL_ONLY: Requires full human intervention

Uses pikepdf to preserve existing structure during analysis.
"""

import csv
import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

import pikepdf
from pikepdf import Name, Dictionary, Array


class RemediationLevel(Enum):
    AUTO_FIXABLE = "AUTO_FIXABLE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    MANUAL_ONLY = "MANUAL_ONLY"


class IssueSeverity(Enum):
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    MODERATE = "MODERATE"
    ADVISORY = "ADVISORY"


@dataclass
class AccessibilityIssue:
    """Represents a single accessibility issue found in the PDF."""
    check_id: str
    check_name: str
    category: str
    severity: str
    remediation_level: str
    description: str
    location: str = ""
    recommendation: str = ""
    wcag_criteria: str = ""
    pdfua_section: str = ""


@dataclass
class AssessmentResult:
    """Complete assessment results for a single PDF."""
    filename: str
    filepath: str
    passed: bool = False
    total_issues: int = 0
    critical_count: int = 0
    important_count: int = 0
    moderate_count: int = 0
    advisory_count: int = 0
    auto_fixable_count: int = 0
    human_review_count: int = 0
    manual_only_count: int = 0
    issues: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    structure_info: dict = field(default_factory=dict)


# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input_pdfs"
OUTPUT_DIR = SCRIPT_DIR / "staged_compliance"
ASSESSMENT_DIR = SCRIPT_DIR / "assessment_results"
REPORT_PATH = ASSESSMENT_DIR / "accessibility_assessment.csv"
DETAILS_PATH = ASSESSMENT_DIR / "detailed_report.json"


def check_metadata_compliance(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Check metadata requirements (AUTO_FIXABLE)."""
    
    # Check Title
    title = pdf.Root.get("/Title")
    if not title:
        result.issues.append(AccessibilityIssue(
            check_id="META-001",
            check_name="Missing Document Title",
            category="Metadata",
            severity=IssueSeverity.CRITICAL.value,
            remediation_level=RemediationLevel.AUTO_FIXABLE.value,
            description="Document /Title metadata is missing",
            location="Document Catalog",
            recommendation="Set meaningful title in metadata (not just filename)",
            wcag_criteria="WCAG 2.4.2",
            pdfua_section="ISO 14289-1:2014 §7.1"
        ))
    else:
        result.metadata["title"] = str(title)
    
    # Check Language
    lang = pdf.Root.get("/Lang")
    if not lang:
        result.issues.append(AccessibilityIssue(
            check_id="META-002",
            check_name="Missing Document Language",
            category="Metadata",
            severity=IssueSeverity.CRITICAL.value,
            remediation_level=RemediationLevel.AUTO_FIXABLE.value,
            description="Document /Lang is not set in Catalog",
            location="Document Catalog",
            recommendation="Set language code (e.g., 'en-US') for screen readers",
            wcag_criteria="WCAG 3.1.1",
            pdfua_section="ISO 14289-1:2014 §7.2"
        ))
    else:
        result.metadata["language"] = str(lang)
    
    # Check DisplayDocTitle
    viewer_prefs = pdf.Root.get("/ViewerPreferences")
    display_title = False
    if viewer_prefs:
        display_title = viewer_prefs.get("/DisplayDocTitle") == True
    
    if not display_title:
        result.issues.append(AccessibilityIssue(
            check_id="META-003",
            check_name="DisplayDocTitle Not Set",
            category="Metadata",
            severity=IssueSeverity.MODERATE.value,
            remediation_level=RemediationLevel.AUTO_FIXABLE.value,
            description="ViewerPreferences.DisplayDocTitle should be true",
            location="ViewerPreferences",
            recommendation="Set DisplayDocTitle to true so title shows in title bar",
            wcag_criteria="WCAG 2.4.2",
            pdfua_section="ISO 14289-1:2014 §7.1"
        ))
    
    # Check Author (recommended)
    try:
        docinfo = pdf.docinfo
        author = docinfo.get("/Author")
        if author:
            result.metadata["author"] = str(author)
    except Exception:
        pass


def check_structure_tree(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Check tags tree structure (MIXED)."""
    
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    
    if not struct_tree_root:
        result.issues.append(AccessibilityIssue(
            check_id="STRUCT-001",
            check_name="Missing Structure Tree Root",
            category="Structure",
            severity=IssueSeverity.CRITICAL.value,
            remediation_level=RemediationLevel.MANUAL_ONLY.value,
            description="No /StructTreeRoot found - document is untagged",
            location="Document Catalog",
            recommendation="Document requires full tagging structure (manual process)",
            wcag_criteria="WCAG 1.3.1, 4.1.2",
            pdfua_section="ISO 14289-1:2014 §5"
        ))
        result.structure_info["has_struct_tree"] = False
        return
    
    result.structure_info["has_struct_tree"] = True
    
    # Check MarkInfo
    mark_info = pdf.Root.get("/MarkInfo")
    is_marked = False
    if mark_info:
        marked = mark_info.get("/Marked")
        is_marked = marked is True or marked == Name("/true")
    
    result.structure_info["is_marked"] = is_marked
    
    if not is_marked:
        result.issues.append(AccessibilityIssue(
            check_id="STRUCT-002",
            check_name="MarkInfo Not Set to Marked",
            category="Structure",
            severity=IssueSeverity.CRITICAL.value,
            remediation_level=RemediationLevel.AUTO_FIXABLE.value,
            description="/MarkInfo -> /Marked is not set to true",
            location="Document Catalog /MarkInfo",
            recommendation="Set MarkInfo.Marked to true",
            wcag_criteria="WCAG 4.1.2",
            pdfua_section="ISO 14289-1:2014 §5.3"
        ))
    
    # Traverse structure tree and count elements
    tag_counts = {}
    untagged_content = []
    
    def traverse_struct_tree(node, depth=0):
        if node is None:
            return
        
        # Handle pikepdf Array objects
        if isinstance(node, list) or (hasattr(node, '__class__') and 'Array' in node.__class__.__name__):
            try:
                for item in node:
                    traverse_struct_tree(item, depth)
            except Exception:
                pass
            return
        
        # Must be a Dictionary-like object to have keys
        if not hasattr(node, 'get'):
            return
        
        try:
            # Get the type of structure element
            elem_type = node.get("/S")
            if elem_type:
                type_name = str(elem_type)
                tag_counts[type_name] = tag_counts.get(type_name, 0) + 1
                
                # Check for missing alt text on figures
                if elem_type == Name("/Figure"):
                    alt_text = node.get("/Alt")
                    if not alt_text or alt_text == "":
                        result.issues.append(AccessibilityIssue(
                            check_id="FIG-001",
                            check_name="Figure Missing Alt Text",
                            category="Figures",
                            severity=IssueSeverity.CRITICAL.value,
                            remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                            description="Figure element has no /Alt text",
                            location=f"Structure tree (depth {depth})",
                            recommendation="Add meaningful alternative text describing the image",
                            wcag_criteria="WCAG 1.1.1",
                            pdfua_section="ISO 14289-1:2014 §5.6"
                        ))
            
            # Check children
            children = node.get("/K")
            if children:
                traverse_struct_tree(children, depth + 1)
        except Exception:
            pass  # Skip nodes that can't be processed
    
    # Start traversal from root elements
    parent_tree = struct_tree_root.get("/ParentTree")
    k_array = struct_tree_root.get("/K")
    
    if k_array:
        if isinstance(k_array, list):
            for item in k_array:
                traverse_struct_tree(item)
        else:
            traverse_struct_tree(k_array)
    
    result.structure_info["tag_counts"] = tag_counts
    
    # Check for proper heading hierarchy
    heading_tags = [k for k in tag_counts.keys() if k.startswith("/H") and k != "/Heading"]
    heading_counts = {k: v for k, v in tag_counts.items() if k.startswith("/H") and k != "/Heading"}
    
    if heading_tags:
        # Check for H1
        if "/H1" not in tag_counts and "/H" not in tag_counts:
            result.issues.append(AccessibilityIssue(
                check_id="HEAD-001",
                check_name="No H1 Heading Found",
                category="Headings",
                severity=IssueSeverity.IMPORTANT.value,
                remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                description="Document has headings but no H1 (main heading)",
                location="Structure tree",
                recommendation="Ensure document starts with H1 heading",
                wcag_criteria="WCAG 1.3.1",
                pdfua_section="ISO 14289-1:2014 §5.4"
            ))
        
        # Check for multiple H1s
        h1_count = heading_counts.get("/H1", 0)
        if h1_count > 1:
            result.issues.append(AccessibilityIssue(
                check_id="HEAD-003",
                check_name="Multiple H1 Headings",
                category="Headings",
                severity=IssueSeverity.IMPORTANT.value,
                remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                description=f"Document has {h1_count} H1 headings (should typically have one)",
                location="Structure tree",
                recommendation="Use only one H1 per document (main title), use H2+ for sections",
                wcag_criteria="WCAG 1.3.1",
                pdfua_section="ISO 14289-1:2014 §5.4"
            ))
        
        # Check for skipped levels (basic - just existence)
        has_h = "/H" in tag_counts
        if not has_h:
            heading_levels = []
            for i in range(1, 7):
                if f"/H{i}" in tag_counts:
                    heading_levels.append(i)
            
            if len(heading_levels) > 1:
                for i in range(len(heading_levels) - 1):
                    if heading_levels[i+1] - heading_levels[i] > 1:
                        result.issues.append(AccessibilityIssue(
                            check_id="HEAD-002",
                            check_name="Skipped Heading Level",
                            category="Headings",
                            severity=IssueSeverity.IMPORTANT.value,
                            remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                            description=f"Heading levels skip from H{heading_levels[i]} to H{heading_levels[i+1]}",
                            location="Structure tree",
                            recommendation="Fix heading hierarchy - do not skip levels",
                            wcag_criteria="WCAG 1.3.1",
                            pdfua_section="ISO 14289-1:2014 §5.4"
                        ))
    
    result.structure_info["heading_counts"] = {k.replace("/H", ""): v for k, v in heading_counts.items()}
    
    # Check heading SEQUENCE (order they appear in document)
    heading_sequence = []
    
    def collect_headings(node, order=0):
        if node is None:
            return
        
        # Handle arrays
        if isinstance(node, list) or (hasattr(node, '__class__') and 'Array' in node.__class__.__name__):
            try:
                for idx, item in enumerate(node):
                    collect_headings(item, order + idx)
            except Exception:
                pass
            return
        
        if not hasattr(node, 'get'):
            return
        
        try:
            elem_type = node.get("/S")
            if elem_type:
                type_str = str(elem_type)
                if type_str.startswith("/H") and type_str != "/Heading" and len(type_str) <= 3:
                    # Extract level number
                    try:
                        level = int(type_str[2:])
                        heading_sequence.append((level, type_str))
                    except ValueError:
                        pass
            
            # Recurse
            children = node.get("/K")
            if children:
                collect_headings(children, order + 1)
        except Exception:
            pass
    
    k_array = struct_tree_root.get("/K")
    if k_array:
        collect_headings(k_array)
    
    # Analyze heading sequence for order violations
    if len(heading_sequence) > 1:
        # Check if first heading is H1
        if heading_sequence[0][0] != 1:
            result.issues.append(AccessibilityIssue(
                check_id="HEAD-004",
                check_name="First Heading Is Not H1",
                category="Headings",
                severity=IssueSeverity.IMPORTANT.value,
                remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                description=f"Document starts with H{heading_sequence[0][0]} instead of H1",
                location=f"First heading in sequence: {heading_sequence[0][1]}",
                recommendation="First heading should be H1 (main document title)",
                wcag_criteria="WCAG 1.3.1",
                pdfua_section="ISO 14289-1:2014 §5.4"
            ))
        
        # Check for skipped levels in sequence
        prev_level = 0
        for i, (level, tag) in enumerate(heading_sequence):
            if prev_level > 0 and level > prev_level + 1:
                result.issues.append(AccessibilityIssue(
                    check_id="HEAD-005",
                    check_name="Skipped Heading Level in Sequence",
                    category="Headings",
                    severity=IssueSeverity.IMPORTANT.value,
                    remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                    description=f"Heading sequence skips from H{prev_level} to H{level}",
                    location=f"Position {i} in heading sequence: {tag}",
                    recommendation="Do not skip heading levels (H1 → H2 → H3, not H1 → H3)",
                    wcag_criteria="WCAG 1.3.1",
                    pdfua_section="ISO 14289-1:2014 §5.4"
                ))
            prev_level = level
    
    result.structure_info["heading_sequence_length"] = len(heading_sequence)


def check_tables(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Check table structure (MIXED)."""
    
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if not struct_tree_root:
        return
    
    table_count = 0
    tables_with_headers = 0
    tables_missing_headers = 0
    
    def check_table(node):
        nonlocal table_count, tables_with_headers, tables_missing_headers
        
        if node is None:
            return
        
        # Handle arrays
        if isinstance(node, list) or (hasattr(node, '__class__') and 'Array' in node.__class__.__name__):
            try:
                for item in node:
                    check_table(item)
            except Exception:
                pass
            return
        
        if not hasattr(node, 'get'):
            return
        
        try:
            elem_type = node.get("/S")
            
            if elem_type == Name("/Table"):
                table_count += 1
                has_th = False
                
                # Check children for TH elements
                children = node.get("/K")
                if children:
                    def find_th(child_node):
                        nonlocal has_th
                        if child_node is None:
                            return
                        # Handle arrays
                        if isinstance(child_node, list) or (hasattr(child_node, '__class__') and 'Array' in child_node.__class__.__name__):
                            try:
                                for c in child_node:
                                    find_th(c)
                            except Exception:
                                pass
                            return
                        if not hasattr(child_node, 'get'):
                            return
                        child_type = child_node.get("/S")
                        if child_type == Name("/TH"):
                            has_th = True
                        # Recurse
                        grandchildren = child_node.get("/K")
                        if grandchildren:
                            find_th(grandchildren)
                    
                    find_th(children)
                
                if has_th:
                    tables_with_headers += 1
                else:
                    tables_missing_headers += 1
                    result.issues.append(AccessibilityIssue(
                        check_id="TAB-001",
                        check_name="Table Missing Header Cells",
                        category="Tables",
                        severity=IssueSeverity.CRITICAL.value,
                        remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                        description=f"Table #{table_count} has no header cells (/TH)",
                        location="Structure tree",
                        recommendation="Identify and tag header cells with /TH and proper scope",
                        wcag_criteria="WCAG 1.3.1, 4.1.2",
                        pdfua_section="ISO 14289-1:2014 §5.7"
                    ))
            
            # Recurse
            children = node.get("/K")
            if children:
                check_table(children)
        except Exception:
            pass
    
    k_array = struct_tree_root.get("/K")
    if k_array:
        if isinstance(k_array, list):
            for item in k_array:
                check_table(item)
        else:
            check_table(k_array)
    
    result.structure_info["table_count"] = table_count
    result.structure_info["tables_with_headers"] = tables_with_headers
    result.structure_info["tables_missing_headers"] = tables_missing_headers


def check_lists(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Check list structure (HUMAN_REVIEW)."""
    
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if not struct_tree_root:
        return
    
    list_count = 0
    
    def check_list(node):
        nonlocal list_count
        
        if node is None:
            return
        
        # Handle arrays
        if isinstance(node, list) or (hasattr(node, '__class__') and 'Array' in node.__class__.__name__):
            try:
                for item in node:
                    check_list(item)
            except Exception:
                pass
            return
        
        if not hasattr(node, 'get'):
            return
        
        try:
            elem_type = node.get("/S")
            
            if elem_type == Name("/L"):
                list_count += 1
                
                # Check for proper L -> LI -> Lbl/LBody structure
                children = node.get("/K")
                if children:
                    has_li = False
                    # Handle array children
                    if isinstance(children, list) or (hasattr(children, '__class__') and 'Array' in children.__class__.__name__):
                        try:
                            for child in children:
                                if hasattr(child, 'get') and child.get("/S") == Name("/LI"):
                                    has_li = True
                                    break
                        except Exception:
                            pass
                    elif hasattr(children, 'get') and children.get("/S") == Name("/LI"):
                        has_li = True
                
                if not has_li:
                    result.issues.append(AccessibilityIssue(
                        check_id="LIST-001",
                        check_name="List Missing List Items",
                        category="Lists",
                        severity=IssueSeverity.IMPORTANT.value,
                        remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                        description=f"List #{list_count} has no /LI elements",
                        location="Structure tree",
                        recommendation="Ensure list contains proper /LI, /Lbl, /LBody structure",
                        wcag_criteria="WCAG 1.3.1",
                        pdfua_section="ISO 14289-1:2014 §5.5"
                    ))
            
            # Recurse
            children = node.get("/K")
            if children:
                check_list(children)
        except Exception:
            pass
    
    k_array = struct_tree_root.get("/K")
    if k_array:
        if isinstance(k_array, list):
            for item in k_array:
                check_list(item)
        else:
            check_list(k_array)
    
    result.structure_info["list_count"] = list_count


def check_links(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Check link annotations (MIXED)."""
    
    link_count = 0
    non_descriptive_count = 0
    
    non_descriptive_patterns = ["click here", "here", "more", "link", "read more", "learn more"]
    
    for page_num, page in enumerate(pdf.pages, 1):
        annots = page.get("/Annots")
        if not annots:
            continue
        
        for annot in annots:
            if annot.get("/Subtype") == Name("/Link"):
                link_count += 1
                
                # Check for alt text
                alt_text = annot.get("/Contents") or annot.get("/NM")
                
                # Get link text if possible (from QuadPoints or associated text)
                # This is limited - full check requires text extraction
                
                if alt_text:
                    alt_lower = str(alt_text).lower()
                    for pattern in non_descriptive_patterns:
                        if pattern in alt_lower:
                            non_descriptive_count += 1
                            result.issues.append(AccessibilityIssue(
                                check_id="LINK-001",
                                check_name="Non-Descriptive Link Text",
                                category="Links",
                                severity=IssueSeverity.IMPORTANT.value,
                                remediation_level=RemediationLevel.HUMAN_REVIEW.value,
                                description=f"Link contains non-descriptive text: '{alt_text}'",
                                location=f"Page {page_num}",
                                recommendation="Use descriptive link text that indicates destination/purpose",
                                wcag_criteria="WCAG 2.4.4",
                                pdfua_section="ISO 14289-1:2014 §5.9"
                            ))
                            break
    
    result.structure_info["link_count"] = link_count
    result.structure_info["non_descriptive_links"] = non_descriptive_count


def check_fonts(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Check font embedding and Unicode mapping (DETECT ONLY)."""
    
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
    
    if unembedded_fonts:
        result.issues.append(AccessibilityIssue(
            check_id="FONT-001",
            check_name="Unembedded Fonts Detected",
            category="Fonts",
            severity=IssueSeverity.IMPORTANT.value,
            remediation_level=RemediationLevel.MANUAL_ONLY.value,
            description=f"Fonts not embedded: {', '.join(unembedded_fonts[:5])}",
            location="Font resources",
            recommendation="Embed all fonts or use system fonts for text accessibility",
            wcag_criteria="WCAG 1.4.1",
            pdfua_section="ISO 14289-1:2014 §5.2"
        ))
    
    if missing_tounicode:
        result.issues.append(AccessibilityIssue(
            check_id="FONT-002",
            check_name="Missing ToUnicode CMap",
            category="Fonts",
            severity=IssueSeverity.IMPORTANT.value,
            remediation_level=RemediationLevel.MANUAL_ONLY.value,
            description=f"Fonts missing Unicode mapping: {', '.join(missing_tounicode[:5])}",
            location="Font resources",
            recommendation="Add ToUnicode CMap to enable text extraction for screen readers",
            wcag_criteria="WCAG 1.3.2",
            pdfua_section="ISO 14289-1:2014 §5.2"
        ))
    
    result.structure_info["unembedded_fonts"] = unembedded_fonts
    result.structure_info["missing_tounicode"] = missing_tounicode


def check_images_xobjects(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Count images and check for alt text coverage."""
    
    total_images = 0
    tagged_images = 0
    
    # Count XObject images
    for page_num, page in enumerate(pdf.pages, 1):
        resources = page.get("/Resources", Dictionary())
        xobjects = resources.get("/XObject", Dictionary())
        
        if not xobjects:
            continue
        
        for key, xobj in xobjects.items():
            if xobj is None:
                continue
            if xobj.get("/Subtype") == Name("/Image"):
                total_images += 1
    
    # Get tagged image count from structure tree
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if struct_tree_root:
        tag_counts = result.structure_info.get("tag_counts", {})
        tagged_images = tag_counts.get("/Figure", 0)
    
    result.structure_info["total_xobject_images"] = total_images
    result.structure_info["tagged_figures"] = tagged_images
    
    # Check for untagged images
    if total_images > tagged_images:
        untagged_count = total_images - tagged_images
        result.issues.append(AccessibilityIssue(
            check_id="IMG-001",
            check_name="Untagged Images Detected",
            category="Figures",
            severity=IssueSeverity.CRITICAL.value,
            remediation_level=RemediationLevel.HUMAN_REVIEW.value,
            description=f"{untagged_count} image(s) are not in the structure tree",
            location=f"Total: {total_images}, Tagged: {tagged_images}",
            recommendation="Add all images to structure tree with /Figure tags and alt text",
            wcag_criteria="WCAG 1.1.1",
            pdfua_section="ISO 14289-1:2014 §5.6"
        ))


def check_security(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Check security settings that block accessibility."""
    
    if pdf.is_encrypted:
        result.issues.append(AccessibilityIssue(
            check_id="SEC-001",
            check_name="Document Is Encrypted",
            category="Security",
            severity=IssueSeverity.CRITICAL.value,
            remediation_level=RemediationLevel.AUTO_FIXABLE.value,
            description="PDF is encrypted/password protected",
            location="Document security",
            recommendation="Remove encryption or ensure accessibility tools can access content",
            wcag_criteria="WCAG 4.1.2",
            pdfua_section="ISO 14289-1:2014 §5.1"
        ))
    
    # Check permissions (if we can access them)
    try:
        perms = pdf.allow
        if not perms.extract:
            result.issues.append(AccessibilityIssue(
                check_id="SEC-002",
                check_name="Content Extraction Disabled",
                category="Security",
                severity=IssueSeverity.CRITICAL.value,
                remediation_level=RemediationLevel.AUTO_FIXABLE.value,
                description="Document permissions block text extraction",
                location="Document security",
                recommendation="Enable content extraction for screen readers",
                wcag_criteria="WCAG 4.1.2",
                pdfua_section="ISO 14289-1:2014 §5.1"
            ))
    except Exception:
        pass


def count_pages(pdf: pikepdf.Pdf) -> int:
    """Count total pages in document."""
    return len(pdf.pages)


def check_reading_order(pdf: pikepdf.Pdf, result: AssessmentResult) -> None:
    """Basic reading order check (limited automation)."""
    
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if not struct_tree_root:
        return
    
    # Check if ParentTree exists (required for content-to-structure mapping)
    parent_tree = struct_tree_root.get("/ParentTree")
    if not parent_tree:
        result.issues.append(AccessibilityIssue(
            check_id="READ-001",
            check_name="Missing Parent Tree",
            category="Reading Order",
            severity=IssueSeverity.IMPORTANT.value,
            remediation_level=RemediationLevel.MANUAL_ONLY.value,
            description="/ParentTree is missing - content-to-structure mapping incomplete",
            location="Structure Tree Root",
            recommendation="Ensure ParentTree maps content streams to structure elements",
            wcag_criteria="WCAG 1.3.2",
            pdfua_section="ISO 14289-1:2014 §5.3"
        ))
    
    result.structure_info["has_parent_tree"] = parent_tree is not None


def assess_pdf(filepath: Path) -> AssessmentResult:
    """Perform complete accessibility assessment on a PDF."""
    
    result = AssessmentResult(
        filename=filepath.stem,
        filepath=str(filepath)
    )
    
    with pikepdf.open(filepath) as pdf:
        # Basic info
        result.metadata["page_count"] = count_pages(pdf)
        
        # Run all checks
        check_metadata_compliance(pdf, result)
        check_structure_tree(pdf, result)
        check_tables(pdf, result)
        check_lists(pdf, result)
        check_links(pdf, result)
        check_fonts(pdf, result)
        check_images_xobjects(pdf, result)
        check_security(pdf, result)
        check_reading_order(pdf, result)
        
        # Calculate summary
        result.total_issues = len(result.issues)
        result.passed = result.total_issues == 0
        
        for issue in result.issues:
            if issue.severity == IssueSeverity.CRITICAL.value:
                result.critical_count += 1
            elif issue.severity == IssueSeverity.IMPORTANT.value:
                result.important_count += 1
            elif issue.severity == IssueSeverity.MODERATE.value:
                result.moderate_count += 1
            elif issue.severity == IssueSeverity.ADVISORY.value:
                result.advisory_count += 1
            
            if issue.remediation_level == RemediationLevel.AUTO_FIXABLE.value:
                result.auto_fixable_count += 1
            elif issue.remediation_level == RemediationLevel.HUMAN_REVIEW.value:
                result.human_review_count += 1
            else:
                result.manual_only_count += 1
    
    return result


def generate_csv_report(results: list[AssessmentResult]) -> None:
    """Generate CSV summary report."""
    
    fieldnames = [
        "Filename", "Passed", "Total_Issues", "Critical", "Important",
        "Moderate", "Advisory", "Auto_Fixable", "Human_Review", "Manual_Only",
        "Page_Count", "Is_Tagged", "Image_Count", "Table_Count"
    ]
    
    with open(REPORT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)
        
        for result in results:
            writer.writerow([
                result.filename,
                result.passed,
                result.total_issues,
                result.critical_count,
                result.important_count,
                result.moderate_count,
                result.advisory_count,
                result.auto_fixable_count,
                result.human_review_count,
                result.manual_only_count,
                result.metadata.get("page_count", 0),
                result.structure_info.get("is_marked", False),
                result.structure_info.get("total_xobject_images", 0),
                result.structure_info.get("table_count", 0)
            ])
    
    print(f"CSV report saved to: {REPORT_PATH}")


def generate_json_report(results: list[AssessmentResult]) -> None:
    """Generate detailed JSON report with all findings."""
    
    output = {
        "assessment_date": str(Path(ASSESSMENT_DIR).stat().st_mtime),
        "total_documents": len(results),
        "summary": {
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "total_issues": sum(r.total_issues for r in results),
            "by_severity": {
                "critical": sum(r.critical_count for r in results),
                "important": sum(r.important_count for r in results),
                "moderate": sum(r.moderate_count for r in results),
                "advisory": sum(r.advisory_count for r in results)
            },
            "by_remediation": {
                "auto_fixable": sum(r.auto_fixable_count for r in results),
                "human_review": sum(r.human_review_count for r in results),
                "manual_only": sum(r.manual_only_count for r in results)
            }
        },
        "documents": []
    }
    
    for result in results:
        doc_data = {
            "filename": result.filename,
            "filepath": result.filepath,
            "passed": result.passed,
            "summary": {
                "total_issues": result.total_issues,
                "critical": result.critical_count,
                "important": result.important_count,
                "moderate": result.moderate_count,
                "advisory": result.advisory_count
            },
            "remediation_breakdown": {
                "auto_fixable": result.auto_fixable_count,
                "human_review": result.human_review_count,
                "manual_only": result.manual_only_count
            },
            "metadata": result.metadata,
            "structure_info": {k: v for k, v in result.structure_info.items() 
                           if not isinstance(v, list)},  # Exclude large lists
            "issues": [asdict(issue) for issue in result.issues]
        }
        output["documents"].append(doc_data)
    
    with open(DETAILS_PATH, "w", encoding="utf-8") as jsonfile:
        json.dump(output, jsonfile, indent=2)
    
    print(f"Detailed JSON report saved to: {DETAILS_PATH}")


def print_summary(results: list[AssessmentResult]) -> None:
    """Print assessment summary to console."""
    
    print("\n" + "=" * 70)
    print("ACCESSIBILITY ASSESSMENT SUMMARY")
    print("=" * 70)
    
    total_docs = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total_docs - passed
    
    print(f"\nDocuments Assessed: {total_docs}")
    print(f"  Passed (no issues): {passed}")
    print(f"  Failed (issues found): {failed}")
    
    total_issues = sum(r.total_issues for r in results)
    print(f"\nTotal Issues Found: {total_issues}")
    
    print("\nBy Severity:")
    print(f"  CRITICAL:     {sum(r.critical_count for r in results)}")
    print(f"  IMPORTANT:    {sum(r.important_count for r in results)}")
    print(f"  MODERATE:     {sum(r.moderate_count for r in results)}")
    print(f"  ADVISORY:     {sum(r.advisory_count for r in results)}")
    
    print("\nBy Remediation Level:")
    print(f"  AUTO_FIXABLE:   {sum(r.auto_fixable_count for r in results)}")
    print(f"  HUMAN_REVIEW:   {sum(r.human_review_count for r in results)}")
    print(f"  MANUAL_ONLY:    {sum(r.manual_only_count for r in results)}")
    
    print("\n" + "-" * 70)
    print("REMEDIATION PRIORITY")
    print("-" * 70)
    
    # List documents by priority (most critical issues first)
    sorted_results = sorted(results, key=lambda r: (-r.critical_count, -r.important_count))
    
    for result in sorted_results:
        if result.total_issues > 0:
            priority = "HIGH" if result.critical_count > 0 else "MEDIUM" if result.important_count > 0 else "LOW"
            print(f"\n{result.filename}")
            print(f"  Priority: {priority}")
            print(f"  Issues: {result.total_issues} (C:{result.critical_count} I:{result.important_count} M:{result.moderate_count} A:{result.advisory_count})")
            print(f"  Auto-fixable: {result.auto_fixable_count} | Human review: {result.human_review_count} | Manual: {result.manual_only_count}")
    
    print("\n" + "=" * 70)


def main():
    """Main entry point for accessibility assessment."""
    
    print("=" * 70)
    print("ADA Accessibility Assessment Tool")
    print("=" * 70)
    
    # Ensure output directories exist
    ASSESSMENT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find PDFs in input directory
    if not INPUT_DIR.exists():
        print(f"Error: Input directory not found: {INPUT_DIR}")
        return
    
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in: {INPUT_DIR}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to assess\n")
    
    # Assess each PDF
    results = []
    for pdf_path in pdf_files:
        print(f"Assessing: {pdf_path.name}")
        
        try:
            result = assess_pdf(pdf_path)
            results.append(result)
            
            status = "✓ PASS" if result.passed else f"✗ FAIL ({result.total_issues} issues)"
            print(f"  -> {status}")
            
        except Exception as e:
            print(f"  -> ERROR: {e}")
            results.append(AssessmentResult(
                filename=pdf_path.stem,
                filepath=str(pdf_path),
                issues=[AccessibilityIssue(
                    check_id="ERR-001",
                    check_name="Assessment Error",
                    category="Error",
                    severity=IssueSeverity.CRITICAL.value,
                    remediation_level=RemediationLevel.MANUAL_ONLY.value,
                    description=f"Could not assess PDF: {e}",
                    location="N/A",
                    recommendation="Check if file is a valid PDF"
                )]
            ))
    
    # Generate reports
    print()
    generate_csv_report(results)
    generate_json_report(results)
    
    # Print summary
    print_summary(results)
    
    print(f"\nOutput directory: {ASSESSMENT_DIR}")
    print("Review detailed_report.json for issue locations and recommendations")


if __name__ == "__main__":
    main()
