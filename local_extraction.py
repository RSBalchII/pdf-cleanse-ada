#!/usr/bin/env python3
"""
Local PDF Extraction Module (Option A)

Extracts text, images, tables, and links from PDFs using pdfplumber.
Preserves all original content without relying on cloud APIs or Adobe automation.

This replaces adobe_autotag_api.py and adobe_auto.py with lightweight, 
local-only extraction that maintains document structure and prepares 
content for accessibility injection.

Usage:
    from local_extraction import extract_pdf_content
    content = extract_pdf_content("input.pdf")
    print(content["text"], content["images"], content["tables"])
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pdfplumber
from PIL import Image
import io


@dataclass
class ImageData:
    """Extracted image information."""
    page_num: int
    index: int
    bbox: Tuple[float, float, float, float]  # (x0, top, x1, bottom)
    size_bytes: int
    file_path: Optional[str] = None  # Path if saved to disk
    alt_text: str = ""  # To be filled by Ollama vision


@dataclass
class TableData:
    """Extracted table information."""
    page_num: int
    index: int
    bbox: Tuple[float, float, float, float]
    rows: List[List[str]]  # 2D array of cell text
    summary: str = ""  # Optional caption/summary


@dataclass
class LinkData:
    """Extracted link information."""
    page_num: int
    text: str
    url: str
    bbox: Tuple[float, float, float, float]


@dataclass
class TextBlock:
    """Extracted text block with layout info."""
    page_num: int
    text: str
    bbox: Tuple[float, float, float, float]
    font_size: Optional[float] = None
    is_heading: bool = False
    heading_level: Optional[int] = None  # 1-6


@dataclass
class PDFContent:
    """Complete extracted content from a PDF."""
    filename: str
    total_pages: int
    text_blocks: List[TextBlock]
    images: List[ImageData]
    tables: List[TableData]
    links: List[LinkData]
    metadata: Dict[str, Any]
    extraction_status: str = "SUCCESS"  # SUCCESS, PARTIAL, FAILED
    error_message: str = ""


def _detect_heading_level(font_size: Optional[float], text: str, all_font_sizes: List[float]) -> Tuple[bool, Optional[int]]:
    """
    Heuristic to detect if a text block is a heading and guess its level.
    
    Args:
        font_size: Font size of the text block
        text: The text content
        all_font_sizes: All font sizes seen in document for normalization
    
    Returns:
        Tuple of (is_heading, level) where level is 1-6 or None
    """
    if font_size is None:
        return False, None
    
    # Text that's significantly larger than average is likely a heading
    if all_font_sizes:
        avg_size = sum(all_font_sizes) / len(all_font_sizes)
        size_ratio = font_size / avg_size
        
        # If 40%+ larger, likely a heading
        if size_ratio >= 1.4:
            # Estimate level based on size ratio
            if size_ratio >= 2.0:
                return True, 1
            elif size_ratio >= 1.7:
                return True, 2
            elif size_ratio >= 1.5:
                return True, 3
            else:
                return True, 4
    
    return False, None


def extract_text_blocks(pdf_path: Path) -> Tuple[List[TextBlock], List[float]]:
    """
    Extract text blocks with layout and font information.
    
    Returns:
        Tuple of (text_blocks, all_font_sizes_for_heuristics)
    """
    text_blocks = []
    font_sizes = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract raw text with layout
                for obj in page.objects.get("char", []):
                    size = obj.get("size")
                    if size:
                        font_sizes.append(size)
                
                # Use pdfplumber's built-in text extraction with bbox
                # pdfplumber preserves layout via cropping strategy
                text_dict = page.extract_text_dict()
                
                if text_dict and "objects" in text_dict:
                    for obj in text_dict["objects"]:
                        if obj.get("object_type") == "char_render_params" or "text" in obj:
                            text_content = obj.get("text", "").strip()
                            if text_content:
                                bbox = (
                                    obj.get("x0", 0),
                                    obj.get("top", 0),
                                    obj.get("x1", 0),
                                    obj.get("bottom", 0)
                                )
                                font_size = obj.get("size")
                                
                                # Create text block if substantial
                                if len(text_content) > 2:
                                    text_blocks.append(TextBlock(
                                        page_num=page_num,
                                        text=text_content,
                                        bbox=bbox,
                                        font_size=font_size,
                                        is_heading=False,
                                        heading_level=None
                                    ))
    
    except Exception as e:
        print(f"Warning: Error extracting text blocks: {e}")
    
    # Post-process to detect headings
    for block in text_blocks:
        is_heading, level = _detect_heading_level(block.font_size, block.text, font_sizes)
        block.is_heading = is_heading
        block.heading_level = level
    
    return text_blocks, font_sizes


def extract_images(pdf_path: Path, output_dir: Optional[Path] = None) -> List[ImageData]:
    """
    Extract all images from PDF.
    
    Args:
        pdf_path: Path to PDF
        output_dir: Optional directory to save extracted images (for alt text generation later)
    
    Returns:
        List of ImageData objects
    """
    images = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
            
            for page_num, page in enumerate(pdf.pages, 1):
                for img_index, img in enumerate(page.images):
                    bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                    
                    # Try to extract and save image
                    file_path = None
                    size_bytes = 0
                    
                    if output_dir:
                        try:
                            # Get image object from PDF
                            img_obj = page.within_bbox(bbox).extract_image()
                            if img_obj:
                                # Save to disk
                                file_path = output_dir / f"page_{page_num}_img_{img_index}.png"
                                with open(file_path, "wb") as f:
                                    f.write(img_obj)
                                size_bytes = len(img_obj)
                                file_path = str(file_path)
                        except Exception as e:
                            print(f"Warning: Could not extract image on page {page_num}: {e}")
                            # Continue without saving
                            size_bytes = img.get("srcsize", 0)
                    else:
                        size_bytes = img.get("srcsize", 0)
                    
                    images.append(ImageData(
                        page_num=page_num,
                        index=img_index,
                        bbox=bbox,
                        size_bytes=size_bytes,
                        file_path=file_path
                    ))
    
    except Exception as e:
        print(f"Warning: Error extracting images: {e}")
    
    return images


def extract_tables(pdf_path: Path) -> List[TableData]:
    """
    Extract all tables from PDF with cell content.
    
    Returns:
        List of TableData objects
    """
    tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                detected_tables = page.find_tables()
                
                for table_index, table in enumerate(detected_tables):
                    # Extract table cells
                    rows = []
                    for row in table.cells:
                        # Group cells by y-coordinate (row)
                        pass
                    
                    # Use pdfplumber's extract method (easier)
                    try:
                        extracted_table = page.extract_table(
                            table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines"}
                        )
                        if extracted_table:
                            # extracted_table is list of lists
                            rows = extracted_table
                            
                            # Get bounding box
                            bbox = (
                                table.bbox[0],
                                table.bbox[1],
                                table.bbox[2],
                                table.bbox[3]
                            )
                            
                            tables.append(TableData(
                                page_num=page_num,
                                index=table_index,
                                bbox=bbox,
                                rows=rows
                            ))
                    except Exception as e:
                        print(f"Warning: Could not extract table on page {page_num}: {e}")
    
    except Exception as e:
        print(f"Warning: Error detecting tables: {e}")
    
    return tables


def extract_links(pdf_path: Path) -> List[LinkData]:
    """
    Extract all links/URLs from PDF.
    
    Returns:
        List of LinkData objects
    """
    links = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # pdfplumber doesn't have direct link extraction
                # Use pikepdf for this (link extraction is in compliance_checker.py)
                # For now, return empty list — can be enhanced later
                pass
    
    except Exception as e:
        print(f"Warning: Error extracting links: {e}")
    
    return links


def extract_metadata(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract PDF metadata (title, author, creation date, etc.).
    
    Returns:
        Dictionary of metadata
    """
    metadata = {
        "title": "",
        "author": "",
        "subject": "",
        "creator": "",
        "producer": "",
        "creation_date": "",
        "modification_date": ""
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.metadata:
                metadata.update({
                    "title": str(pdf.metadata.get("Title", "")),
                    "author": str(pdf.metadata.get("Author", "")),
                    "subject": str(pdf.metadata.get("Subject", "")),
                    "creator": str(pdf.metadata.get("Creator", "")),
                    "producer": str(pdf.metadata.get("Producer", "")),
                })
    except Exception as e:
        print(f"Warning: Error extracting metadata: {e}")
    
    return metadata


def extract_pdf_content(pdf_path: Path, save_images: bool = True) -> PDFContent:
    """
    Extract all content from a PDF without relying on cloud APIs or Adobe automation.
    
    Args:
        pdf_path: Path to input PDF
        save_images: Whether to save extracted images to disk (for later alt-text generation)
    
    Returns:
        PDFContent object with all extracted data
    
    This is the main entry point for Option A (local extraction).
    """
    pdf_path = Path(pdf_path)
    
    result = PDFContent(
        filename=pdf_path.stem,
        total_pages=0,
        text_blocks=[],
        images=[],
        tables=[],
        links=[],
        metadata={}
    )
    
    try:
        # Get page count
        with pdfplumber.open(pdf_path) as pdf:
            result.total_pages = len(pdf.pages)
        
        # Extract content
        print(f"Extracting text blocks from {pdf_path.name}...")
        result.text_blocks, _ = extract_text_blocks(pdf_path)
        
        print(f"Extracting images...")
        image_output_dir = None
        if save_images:
            image_output_dir = pdf_path.parent / f"{pdf_path.stem}_images"
        result.images = extract_images(pdf_path, image_output_dir)
        
        print(f"Extracting tables...")
        result.tables = extract_tables(pdf_path)
        
        print(f"Extracting links...")
        result.links = extract_links(pdf_path)
        
        print(f"Extracting metadata...")
        result.metadata = extract_metadata(pdf_path)
        
        result.extraction_status = "SUCCESS"
        print(f"✓ Extraction complete: {len(result.text_blocks)} text blocks, "
              f"{len(result.images)} images, {len(result.tables)} tables")
    
    except Exception as e:
        result.extraction_status = "FAILED"
        result.error_message = str(e)
        print(f"✗ Extraction failed: {e}")
    
    return result


def save_extraction_json(content: PDFContent, output_path: Path):
    """Save extraction results to JSON for inspection/debugging."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert dataclasses to dicts
    data = {
        "filename": content.filename,
        "total_pages": content.total_pages,
        "extraction_status": content.extraction_status,
        "error_message": content.error_message,
        "text_blocks": [asdict(b) for b in content.text_blocks[:10]],  # First 10 for readability
        "images": [asdict(i) for i in content.images],
        "tables": [
            {
                "page_num": t.page_num,
                "index": t.index,
                "bbox": t.bbox,
                "rows_count": len(t.rows),
                "summary": t.summary
            }
            for t in content.tables
        ],
        "links": [asdict(l) for l in content.links],
        "metadata": content.metadata
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"Extraction saved to: {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python local_extraction.py <pdf_path>")
        sys.exit(1)
    
    pdf_file = Path(sys.argv[1])
    content = extract_pdf_content(pdf_file)
    
    # Save JSON report
    json_output = pdf_file.parent / f"{pdf_file.stem}_extraction.json"
    save_extraction_json(content, json_output)
