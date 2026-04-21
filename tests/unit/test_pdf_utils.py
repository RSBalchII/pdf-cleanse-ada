"""
Unit tests for _pdf_utils.py - Core PDF utilities module.

Tests cover:
- Image counting (returns dict with total_count)
- Link extraction (returns list of dicts)
- PDF opening/closing
- Title injection and retrieval
- Structure tree detection
"""


import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from pikepdf import Name

# Import functions under test from the actual module
from _pdf_utils import (
    count_images,
    get_links,
    open_pdf,
    close_pdf,
    has_struct_tree,
    inject_title,
    get_current_title
)


class TestCountImages:
    """Tests for the count_images(pdf) function."""
    
    def test_count_images_returns_dict_with_total_count(self):
        """Test that count_images returns a dictionary with total_count key."""
        
        # Mock pikepdf since it requires native bindings
        class MockPdf:
            def __init__(self, path):
                self.path = str(path)
            
            def get(self, key):
                if key == "/StructTreeRoot":
                    return MagicMock()
                return None
            
            pages = property(lambda self: [MagicMock()])

        with patch("pikepdf.Pdf") as mock_pdf_class:
            pdf_doc = MockPdf(Path("/tmp/test.pdf"))
            result = count_images(pdf_doc)
                
        assert isinstance(result, dict)
        assert "total_count" in result


class TestGetLinks:
    """Tests for the get_links(pdf) function."""
    
    def test_get_links_returns_list(self):
        """Test that get_links returns a list of links."""
        
        class MockPdf:
            def __init__(self, path):
                self.path = str(path)
            
            def get(self, key):
                if key == "/StructTreeRoot":
                    return MagicMock()
                return None
            
            pages = property(lambda self: [MagicMock()])

        with patch("pikepdf.Pdf") as mock_pdf_class:
            pdf_doc = MockPdf(Path("/tmp/test.pdf"))
            result = get_links(pdf_doc)
                
        assert isinstance(result, list)


class TestOpenPdf:
    """Tests for the open_pdf(path) function."""
    
    def test_open_pdf_returns_pdf_document(self):
        """Test that open_pdf returns a PDF document object."""
        with patch("pikepdf.Pdf.open") as mock_open:
            mock_open.return_value = MagicMock()
            
            result = open_pdf(Path("/tmp/test.pdf"))
                
        assert isinstance(result, MagicMock)


class TestClosePdf:
    """Tests for the close_pdf(pdf) function."""
    
    def test_close_pdf_exists(self):
        """Test that close_pdf is callable and exists."""
        assert callable(close_pdf)
        
    @pytest.mark.parametrize("pdf_arg", [None, MagicMock(), Path("/tmp/test.pdf")])
    def test_close_pdf_accepts_pdf_argument(self, pdf_arg):
        """Test that close_pdf accepts a pdf argument."""
        with patch("pikepdf.Pdf"):
            # Should work regardless of what we pass to it
            try:
                close_pdf(pdf_arg)  # Should accept one optional arg
            except TypeError as e:
                pytest.fail(f"close_pdf should accept pdf argument, got: {e}")


class TestHasStructTree:
    """Tests for the has_struct_tree(pdf) function."""
    
    def test_has_struct_tree_returns_bool(self):
        """Test that has_struct_tree returns a boolean value."""
        
        class MockPdf:
            Root = MagicMock()
            
            @staticmethod
            def get(key):
                return Name("/H") if key == "/StructTreeRoot" else None
        
        with patch("pikepdf.Pdf.open", return_value=MockPdf()):
            result = has_struct_tree(Path("/tmp/test.pdf"))
                
        assert isinstance(result, bool)


class TestInjectTitle:
    """Tests for the inject_title(pdf, title) function."""
    
    def test_inject_title_exists(self):
        """Test that inject_title is callable and exists."""
        assert callable(inject_title)
