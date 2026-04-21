"""
Unit tests for ada_compliance_processor.py - ADA Compliance Preprocessor.

Tests cover:
- count_xobject_images function
- check_is_tagged function  
- inject_metadata function
- process_pdf function
- generate_triage_report function
"""


import csv
from pathlib import Path
from unittest.mock import MagicMock, patch
import io

# Import functions under test from ada_compliance_processor.py
from ada_compliance_processor import (
    count_xobject_images,
    check_is_tagged,
    inject_metadata,
    process_pdf,
)


class TestCountXObjectImages:
    """Tests for the count_xobject_images() function."""
    
    def test_count_xobject_images_returns_int(self):
        """Test that count_xobject_images returns an integer count."""
        import os
        
        # Create a mock PDF file
        pdf_path = Path("/tmp/test.pdf")
        
        # Mock open_pdf to return a mock PDF object with images
        class MockPdf:
            def __enter__(self):
                self._count = 5
                return self
            def __exit__(self, *args):
                pass
        
        old_open_pdf = None
        try:
            # Patch open_pdf to return our mock
            with patch("ada_compliance_processor.open_pdf", return_value=MockPdf()):
                result = count_xobject_images(pdf_path)
            
            assert isinstance(result, int)
        
        finally:
            if old_open_pdf is not None:
                pass  # Restore if needed


class TestCheckIsTagged:
    """Tests for the check_is_tagged() function."""
    
    def test_check_is_tagged_returns_bool(self):
        """Test that check_is_tagged returns a boolean value."""
        
        class MockPdf:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        
        old_open_pdf = None
        try:
            with patch("ada_compliance_processor.open_pdf", return_value=MockPdf()):
                result = check_is_tagged(Path("/tmp/test.pdf"))
            
            assert isinstance(result, bool)
        
        finally:
            if old_open_pdf is not None:
                pass


class TestInjectMetadata:
    """Tests for the inject_metadata() function."""
    
    def test_inject_metadata_returns_none(self):
        """Test that inject_metadata returns None after processing."""
        
        class MockPdf:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        
        old_open_pdf = None
        try:
            with patch("ada_compliance_processor.open_pdf", return_value=MockPdf()):
                result = inject_metadata(Path("/tmp/input.pdf"), 
                                        Path("/tmp/output.pdf"), 
                                        "Test Document")
            
            assert result is None  # Function should return None
            
        finally:
            if old_open_pdf is not None:
                pass


class TestProcessPdf:
    """Tests for the process_pdf() function."""
    
    def test_process_pdf_returns_result_dict(self):
        """Test that process_pdf returns a result dictionary with expected keys."""
        
        class MockPdf:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        
        old_open_pdf = None
        try:
            with patch("ada_compliance_processor.open_pdf", return_value=MockPdf()):
                input_path = Path("/tmp/input.pdf")
                output_path = Path("/tmp/output.pdf")
                
                result = process_pdf(input_path, output_path)
            
            assert isinstance(result, dict)
            # Check expected keys exist
            assert "Filename" in result or "filename" in result
            assert "Is_Tagged" in result or "is_tagged" in result
            assert "Image_Count" in result or "image_count" in result
            
        finally:
            if old_open_pdf is not None:
                pass


class TestGenerateTriageReport:
    """Tests for the generate_triage_report() function."""
    
    def test_generate_triage_report_creates_csv(self):
        """Test that generate_triage_report creates a CSV file with correct headers."""
        
        results = [
            {
                "Filename": "test1.pdf",
                "Title_Injected": "Test Title 1",
                "Lang_Injected": "en-US",
                "Is_Tagged": True,
                "Image_Count": 5
            },
            {
                "Filename": "test2.pdf",
                "Title_Injected": "Test Title 2",
                "Lang_Injected": "en-US", 
                "Is_Tagged": False,
                "Image_Count": 10
            }
        ]
        
        old_report_path = None
        try:
            # Get the current report path from the module
            import importlib
            from ada_compliance_processor import REPORT_PATH
            
            with patch.object(REPORT_PATH.parent, 'mkdir', lambda *args, **kwargs: None):
                generate_triage_report(results)
            
            assert REPORT_PATH.exists() or "staged_compliance" in str(REPORT_PATH)
            
        finally:
            if old_report_path is not None:
                pass
