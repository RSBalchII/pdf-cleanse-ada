# pytest configuration and fixtures for PDF ADA Compliance Processor tests


import os
from pathlib import Path

# Ensure tests run in the project root directory
TESTS_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = TESTS_DIR


def get_pdf_path(name: str, folder: str = "input_pdfs") -> Path:
    """Helper to get a PDF test file path."""
    return (TESTS_DIR / folder).joinpath(f"{name}.pdf")


# Import pytest fixtures after defining them to ensure they're available
import pytest


def test_base_dir(tmp_path):
    """Provide a temporary base directory for tests."""
    return tmp_path


def clean_test_dirs():
    """Clean up test directories after each function."""
    dirs = [TESTS_DIR / "input_pdfs", TESTS_DIR / "staged_compliance", 
            TESTS_DIR / "adobe_tagged", TESTS_DIR / "auto_fixed"]
    
    for d in dirs:
        if d.exists():
            import shutil
            shutil.rmtree(d)


# Mock pikepdf for testing since it requires native bindings
def mock_pikepdf(monkeypatch):
    """Mock pikepdf operations to avoid native dependency issues."""
    class MockPdf:
        def __init__(self, path):
            self.path = str(path)
        
        def get(self, key):
            if key == "/Title":
                return "Test Document Title"
            elif key == "/Lang":
                from pikepdf import Name
                return Name("/en-US")
            elif key == "/ViewerPreferences":
                class MockPrefs:
                    def get(self, key):
                        if key == "/DisplayDocTitle":
                            return True
                        return False
                    def __repr__(self):
                        return "MockViewerPreferences"
                return MockPrefs()
            elif key == "/StructTreeRoot":
                from pikepdf import Name
                return Name("/H")
            elif key == "/MarkInfo":
                class MockMarkInfo:
                    def get(self, key):
                        if key == "/Marked":
                            return True
                        return None
                    def __repr__(self):
                        return "MockMarkInfo"
                return MockMarkInfo()
            else:
                return None
        
        def pages(self):
            class MockPage:
                def get_page_number(self):
                    return 1
            return [MockPage()]

    class Name:
        def __init__(self, value):
            self.value = value
        
        def __repr__(self):
            return f"Name('{self.value}')"
