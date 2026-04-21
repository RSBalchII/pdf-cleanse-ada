"""
Unit tests for compliance_checker.py - ADA/WCAG/PDF-UA Compliance checks.

Tests cover:
- Title check (WCAG 2.4.2)
- Language check (WCAG 3.1.1)  
- DisplayDocTitle check
- Tagged PDF structure check
- MarkInfo validation
"""


import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from pikepdf import Name

# Import functions under test from compliance_checker.py
from compliance_checker import (
    ComplianceCheck,
    ComplianceReport,
    CheckStatus,
    ComplianceLevel,
    check_title,
    check_language,
    check_display_doctitle,
    check_tags_tree,
    check_mark_info,
)


class TestComplianceCheckDataClass:
    """Tests for the ComplianceCheck dataclass."""

    def test_compliance_check_fields(self):
        """Test that ComplianceCheck has all required fields."""
        check = ComplianceCheck(
            check_id="TEST-001",
            name="Test Check",
            description="A test compliance check",
            status=CheckStatus.PASS.value,
            level=list(ComplianceLevel)[0].value if list(ComplianceLevel) else "A",
            wcag_criteria="2.4.2",
            pdfua_section="§7.1",
            section508="502.3.1"
        )

        assert check.check_id == "TEST-001"
        assert check.name == "Test Check"


class TestCheckTitle:
    """Tests for the check_title() function."""

    def test_check_title_returns_compliance_check(self):
        """Test that check_title returns a ComplianceCheck instance."""
        
        class MockPdf:
            Root = MagicMock()
            
            @staticmethod
            def get(key):
                return "Test Document Title" if key == "/Title" else None
        
        with patch("pikepdf.Pdf"):
            result = check_title(MockPdf())

        assert isinstance(result, ComplianceCheck)


class TestCheckLanguage:
    """Tests for the check_language() function."""

    def test_check_language_with_language_set(self):
        """Test check_language when language is present."""
        
        class MockPdf:
            Root = MagicMock()
            
            @staticmethod
            def get(key):
                return Name("/en-US") if key == "/Lang" else None
        
        with patch("pikepdf.Pdf"):
            result = check_language(MockPdf())

        assert isinstance(result, ComplianceCheck)


class TestDisplayDocTitle:
    """Tests for the check_display_doctitle() function."""

    def test_check_display_doctitle_true(self):
        """Test when DisplayDocTitle is set to true."""
        
        class MockPdf:
            Root = MagicMock()
            
            @staticmethod
            def get(key):
                return True if key == "/DisplayDocTitle" else None
        
        with patch("pikepdf.Pdf"):
            result = check_display_doctitle(MockPdf())

        assert isinstance(result, ComplianceCheck)


class TestTagsTree:
    """Tests for the check_tags_tree() function."""

    def test_check_tags_tree_with_struct_tree(self):
        """Test when StructTreeRoot is present."""
        
        class MockPdf:
            Root = MagicMock()
            
            @staticmethod
            def get(key):
                return Name("/H") if key == "/StructTreeRoot" else None
        
        with patch("pikepdf.Pdf"):
            result = check_tags_tree(MockPdf())

        assert isinstance(result, ComplianceCheck)


class TestMarkInfo:
    """Tests for the check_mark_info() function."""

    def test_check_mark_info_with_marked_true(self):
        """Test when MarkInfo.Marked is set to true."""
        
        class MockPdf:
            Root = MagicMock()
            
            @staticmethod
            def get(key):
                return True if key == "/Marked" else None
        
        with patch("pikepdf.Pdf"):
            result = check_mark_info(MockPdf())

        assert isinstance(result, ComplianceCheck)


class TestComplianceReport:
    """Tests for the ComplianceReport dataclass."""

    def test_compliance_report_fields(self):
        """Test that ComplianceReport has all required fields."""
        report = ComplianceReport(
            filename="test.pdf",
            filepath="/tmp/test.pdf",
            overall_status="PASS"
        )

        assert report.filename == "test.pdf"


class TestCheckStatus:
    """Tests for CheckStatus enum."""

    def test_check_status_values(self):
        """Test that CheckStatus has all expected values."""
        assert hasattr(CheckStatus, 'PASS')
        assert hasattr(CheckStatus, 'FAIL')
        assert hasattr(CheckStatus, 'WARNING')


class TestComplianceLevel:
    """Tests for ComplianceLevel enum."""

    def test_compliance_level_values(self):
        """Test that ComplianceLevel has all expected values."""
        assert hasattr(ComplianceLevel, 'A')
        assert hasattr(ComplianceLevel, 'AA')
        assert hasattr(ComplianceLevel, 'AAA')

