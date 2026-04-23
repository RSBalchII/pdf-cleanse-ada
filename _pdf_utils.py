"""
Core PDF utilities for PDF ADA Compliance Processor.

This module provides common utility functions for:
- Image counting (using pikepdf)
- Link extraction from annotations
- Metadata operations (title, language)
- Structure tree detection

Uses pikepdf for robust PDF structure access and modification.
"""


from pathlib import Path
from typing import Dict, List, Any, Optional
import pikepdf


def count_images(pdf: pikepdf.Pdf) -> Dict[str, int]:
    """Count all images in a PDF document."""
    image_counts = {"total_count": 0}

    try:
        for i, page in enumerate(pdf.pages):
            struct_tree = pdf.Root.get("/StructTreeRoot")

            def count_images_in_node(node, page_num=0):
                if node is None or _is_array(node) and len(list(node)) == 0:
                    return

                if hasattr(node, 'keys') and not isinstance(node, (pikepdf.Pdf, Dictionary)):
                    for child in list(node):
                        count_images_in_node(child, page_num)
                        continue

                try:
                    xobj = node.get("/X")
                    if xobj is not None and hasattr(xobj, 'keys'):
                        image_counts["total_count"] += 1
                except Exception:
                    pass

            k_array = struct_tree.get("/K") if struct_tree else None
            if k_array:
                count_images_in_node(k_array, i)
    except Exception as e:
        image_counts["total_count"] = 0

    return image_counts


def get_links(pdf: pikepdf.Pdf) -> List[Dict[str, Any]]:
    """Extract text from a specific page.

    Args:
        page_num: Page number (0-indexed)
        pdf: Open pikepdf object (optional, defaults to current open)

    Returns:
        Text content of the page as string
    """
    if pdf is None or page_num < 0:
        return ""

    try:
        with pikepdf.open(pdf.path) as curr_pdf:
            page = curr_pdf.pages[page_num]
            
            def collect_text(node, depth=0):
                """Recursively extract text from PDF objects."""
                if node is None or _is_array(node):
                    return
                
                try:
                    elem_type = node.get("/S")
                except Exception:
                    return
                    
                if elem_type == Name("/Text"):
                    try:
                        text_arr = node.get("/T")
                        if isinstance(text_arr, str):
                            return text_arr
                    except Exception:
                        pass

                # Handle text arrays (multiple text objects)
                if hasattr(node, 'keys') and '/T' in node and not isinstance(node.get('/T'), list):
                    try:
                        return str(node['/T'])
                    except Exception:
                        pass

                # Process children recursively
                children = node.get("/K") or []
                for child in children if _is_array(children) else children:
                    collect_text(child, depth + 1)
                
                try:
                    return str(node)
                except Exception:
                    return ""
            
            text = collect_text(page[0])
            return text if text else ""

    except Exception:
        pass
    return ""


def get_all_text(pdf: Optional[pikepdf.Pdf] = None) -> str:
    """Extract all text from the current PDF.
    
    Returns combined text from all pages as single string.
    """
    if pdf is None:
        try:
            with pikepdf.open(Path.cwd() / "input_pdfs" / "test.pdf") as curr_pdf:
                return get_all_text(curr_pdf)
        except Exception:
            pass

    text_parts = []
    for i, page in enumerate(pdf.pages):
        # Use nested function to access parent scope
        def collect(node, depth=0):
            if node is None or _is_array(node):
                return
            
            try:
                elem_type = node.get("/S")
            except Exception:
                pass

            if elem_type == Name("/Text"):
                try:
                    text_arr = node.get("/T")
                    if isinstance(text_arr, str):
                        text_parts.append(str(text_arr))
                except Exception:
                    pass

            children = node.get("/K") or []
            for child in children if _is_array(children) else children:
                collect(child, depth + 1)
        
        try:
            # Get first object of page (complex text stream)
            first_obj = pdf.pages[i][0]
            # Extract text from complex streams using pikepdf's built-in methods
            pass
        except Exception:
            continue

    return ''.join(text_parts)


def _is_array(node):
    """Safely check if a pikepdf object is an Array."""
    try:
        return isinstance(node, (Array, list))
    except Exception:
        return isinstance(node, list)


def get_text_page(page_num: int, pdf: Optional[pikepdf.Pdf] = None) -> str:
    """Extract text from a specific page.

    Args:
        page_num: Page number (0-indexed)
        pdf: Open pikepdf object (optional, defaults to current open)

    Returns:
        Text content of the page as string
    """
    if pdf is None or page_num < 0:
        return ""

    try:
        with pikepdf.open(pdf.path) as curr_pdf:
            page = curr_pdf.pages[page_num]
            
            text_parts = []
            
            def collect_text(node, depth=0):
                """Recursively extract text from PDF objects."""
                if node is None or _is_array(node):
                    return
                
                try:
                    elem_type = node.get("/S")
                except Exception:
                    pass

                if elem_type == Name("/Text"):
                    try:
                        text_arr = node.get("/T")
                        if isinstance(text_arr, str):
                            text_parts.append(str(text_arr))
                    except Exception:
                        pass

                # Process children recursively
                children = node.get("/K") or []
                for child in children if _is_array(children) else children:
                    collect_text(child, depth + 1)
            
            collect_text(page[0])
            return ''.join(text_parts)

    except Exception:
        pass
    return ""


def get_text_page(page_num: int, pdf: Optional[pikepdf.Pdf] = None) -> str:
    """Extract text from a specific page.

    Args:
        page_num: Page number (0-indexed)  
        pdf: Open pikepdf object (optional, defaults to current open)

    Returns:
        Text content of the page as string
    """
    if pdf is None or page_num < 0:
        return ""

    try:
        with pikepdf.open(pdf.path) as curr_pdf:
            page = curr_pdf.pages[page_num]
            
            def collect_text(node, depth=0):
                if node is None or _is_array(node):
                    return
                
                try:
                    elem_type = node.get("/S")
                except Exception:
                    pass

                if elem_type == Name("/Text"):
                    try:
                        text_arr = node.get("/T")
                        if isinstance(text_arr, str):
                            return str(text_arr)
                    except Exception:
                        pass

                children = node.get("/K") or []
                for child in children if _is_array(children) else children:
                    collect_text(child, depth + 1)
            
            text = collect_text(page[0])
            return text if text else ""

    except Exception:
        pass
    return ""
    """
    Count all images in a PDF document.

    Args:
        pdf: Opened pikepdf PDF object

    Returns:
        Dictionary with total_count and page counts per page
    """
    image_counts = {"total_count": 0}
    
    try:
        for i, page in enumerate(pdf.pages):
            # Count images using XObject references from structure tree
            struct_tree = pdf.Root.get("/StructTreeRoot")
            
            def count_images_in_node(node, page_num=0):
                if node is None or isinstance(node, pikepdf.Array) and len(node) == 0:
                    return
                
                # Recursively traverse arrays
                if hasattr(node, '__iter__') and not isinstance(node, (pikepdf.Pdf, pikepdf.Dictionary)):
                    for child in list(node):
                        count_images_in_node(child, page_num)
                    return
                
                # Check for XObject images
                try:
                    xobj = node.get("/X")
                    if xobj is not None and hasattr(xobj, 'get'):
                        image_counts["total_count"] += 1
                except Exception:
                    pass

            k_array = struct_tree.get("/K") if struct_tree else None
            if k_array:
                count_images_in_node(k_array, i)
    except Exception as e:
        # Return default counts on error
        image_counts["total_count"] = 0
    
    return image_counts


def get_links(pdf: pikepdf.Pdf) -> List[Dict[str, Any]]:
    """
    Extract links from a PDF document.

    Args:
        pdf: Opened pikepdf PDF object

    Returns:
        List of dictionaries with link information (type, destination)
    """
    links = []
    
    try:
        struct_tree = pdf.Root.get("/StructTreeRoot")
        
        if not struct_tree or not hasattr(struct_tree, "get"):
            return links
        
        # Get annotation array
        annots = struct_tree.get("/Annots")
        if annots and isinstance(annots, pikepdf.Array):
            
            def extract_links(node):
                if node is None:
                    return
                
                # Try to get link type (S=/D)
                try:
                    link_type = node.get("/S", "")
                except Exception:
                    pass
                
                # Try to get destination (D)
                dest = ""
                try:
                    dest = node.get("/D") or ""
                except Exception:
                    pass
                
                if link_type and dest:
                    links.append({
                        "type": str(link_type),
                        "destination": str(dest)
                    })
                
                # Recursively process children (link array K)
                try:
                    k_array = node.get("/K")
                    if k_array and isinstance(k_array, pikepdf.Array):
                        extract_links(k_array)
                except Exception:
                    pass

            for annot in annots:
                extract_links(annot)
    except Exception as e:
        pass
    
    return links


def open_pdf(path: Path) -> pikepdf.Pdf:
    """
    Open a PDF file and return a pikepdf object.

    Args:
        path: Path to the PDF file

    Returns:
        pikepdf.Pdf object for further processing

    Raises:
        FileNotFoundError: If the PDF doesn't exist
        Exception: On other errors opening the file
    """
    with pikepdf.open(path) as pdf:
        return pdf


def close_pdf(pdf: Optional[pikepdf.Pdf] = None):
    """
    Close a PDF object.

    Args:
        pdf: The pikepdf object to close (optional, defaults to current open)
    """
    if pdf is not None and hasattr(pdf, 'close'):
        try:
            pdf.close()
        except Exception:
            pass


def has_struct_tree(pdf: Optional[pikepdf.Pdf] = None) -> bool:
    """
    Check if a PDF has a structure tree (tagged PDF).

    Args:
        pdf: The pikepdf object to check (optional, defaults to current open)

    Returns:
        True if the document is tagged, False otherwise
    """
    if pdf is None:
        try:
            with open_pdf(Path.cwd() / "input_pdfs" / "test.pdf") as current_pdf:
                return has_struct_tree(current_pdf)
        except Exception:
            pass
    
    struct_tree = pdf.Root.get("/StructTreeRoot")
    return struct_tree is not None


def inject_title(pdf: pikepdf.Pdf, title: str) -> bool:
    """
    Inject a document title into the PDF.

    Args:
        pdf: The pikepdf object to modify
        title: Title string to inject

    Returns:
        True if successful, False on error
    """
    try:
        pdf.Root.set("/Title", title)
        return True
    except Exception as e:
        print(f"Warning: Failed to inject title: {e}")
        return False


def get_current_title(pdf: Optional[pikepdf.Pdf] = None) -> str:
    """
    Get the current document title.

    Args:
        pdf: The pikepdf object to query (optional, defaults to current open)

    Returns:
        Title string or empty string if not set
    """
    if pdf is None:
        try:
            with open_pdf(Path.cwd() / "input_pdfs" / "test.pdf") as current_pdf:
                return get_current_title(current_pdf)
        except Exception:
            pass
    
    title = pdf.Root.get("/Title")
    return str(title) if title else ""
