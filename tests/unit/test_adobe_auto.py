"""
Unit tests for adobe_auto.py - Adobe Acrobat Pro COM Automation.

Tests cover:
- COM initialization/cleanup (win32com)
- PDF opening via Acrobat
- Getting PDF information
- Running accessibility checks
- Saving PDFs
- Opening in Acrobat for review
"""


from pathlib import Path
from unittest.mock import MagicMock, patch


# Import functions under test from adobe_auto.py
from adobe_auto import (
    init_com,
    cleanup_com,
    open_acrobat,
    open_pdf,
    get_pdf_info,
    run_accessibility_check_and_save_report,
    save_pdf,
    close_pdf,
)


class TestInitCleanupCom:
    """Tests for COM initialization and cleanup."""
    
    def test_init_cleanup_com_exist(self):
        """Test that init_com and cleanup_com are callable functions."""
        assert callable(init_com)
        assert callable(cleanup_com)


class TestOpenAcrobat:
    """Tests for the open_acrobat() function."""
    
    def test_open_acrobat_returns_app_object(self):
        """Test that open_acrobat returns an app object (win32com Dispatch)."""
        
        old_init = None
        
        try:
            with patch("adobe_auto.pythoncom.CoInitialize") as mock_init:
                with patch("adobe_auto.win32com.client.Dispatch", return_value=MagicMock()):
                    result = open_acrobat()
                    
            assert isinstance(result, MagicMock)  # Mocked win32com Dispatch
            
        except Exception as e:
            pytest.fail(f"open_acrobat raised unexpected exception: {e}")


class TestOpenPdf:
    """Tests for the open_pdf(app, pdf_path) function."""
    
    def test_open_pdf_returns_av_doc_and_pd_doc(self):
        """Test that open_pdf returns AVDoc and PDDoc objects."""
        
        app_mock = MagicMock()
        
        old_init = None
        
        try:
            with patch("adobe_auto.pythoncom.CoInitialize"):
                with patch("adobe_auto.win32com.client.Dispatch", return_value=MagicMock()):
                    av_doc, pd_doc = open_pdf(app_mock, Path("/tmp/test.pdf"))
                    
            assert isinstance(av_doc, MagicMock)
            assert isinstance(pd_doc, MagicMock)
            
        except Exception as e:
            pytest.fail(f"open_pdf raised unexpected exception: {e}")


class TestGetPdfInfo:
    """Tests for the get_pdf_info(pdDoc) function."""
    
    def test_get_pdf_info_returns_dict(self):
        """Test that get_pdf_info returns a dictionary with PDF info."""
        
        pd_doc = MagicMock()
        pd_doc.GetNumPages.return_value = 5
        
        old_init = None
        
        try:
            result = get_pdf_info(pd_doc)
            
            assert isinstance(result, dict)
            # Check expected keys exist
            assert "num_pages" in result or "num_pages" in str(result.keys())
            
            pd_doc.GetNumPages.assert_called_once()  # Verify the method was called
            
        except Exception as e:
            pytest.fail(f"get_pdf_info raised unexpected exception: {e}")


class TestRunAccessibilityCheckAndSaveReport:
    """Tests for the run_accessibility_check_and_save_report() function."""
    
    def test_run_accessibility_returns_dict(self):
        """Test that run_accessibility_check_and_save_report returns a result dict."""
        
        av_doc = MagicMock()
        pd_doc = MagicMock()
        
        old_init = None
        
        try:
            result = run_accessibility_check_and_save_report(av_doc, 
                                                             pd_doc, 
                                                             "test",
                                                             Path("/tmp/report.json"))
            
            assert isinstance(result, dict)
            # Check expected keys exist
            assert "action" in result or "action" in str(result.keys())
            assert "success" in result or "success" in str(result.keys())
            
        except Exception as e:
            pytest.fail(f"run_accessibility_check_and_save_report raised exception: {e}")


class TestSavePdf:
    """Tests for the save_pdf(pdDoc, output_path) function."""
    
    def test_save_pdf_returns_dict(self):
        """Test that save_pdf returns a result dictionary."""
        
        pd_doc = MagicMock()
        
        old_init = None
        
        try:
            result = save_pdf(pd_doc, Path("/tmp/output.pdf"))
            
            assert isinstance(result, dict)
            # Check expected keys exist  
            assert "action" in result or "action" in str(result.keys())
            assert "success" in result or "success" in str(result.keys())
            
        except Exception as e:
            pytest.fail(f"save_pdf raised unexpected exception: {e}")


class TestClosePdf:
    """Tests for the close_pdf(avDoc, pdDoc, save_changes) function."""
    
    def test_close_pdf_calls_methods(self):
        """Test that close_pdf calls appropriate methods based on parameters."""
        
        av_doc = MagicMock()
        pd_doc = MagicMock()
        
        old_init = None
        
        try:
            with patch("adobe_auto.pythoncom.CoUninitialize"):
                # Test without save changes flag
                close_pdf(av_doc, pd_doc, save_changes=False)
                
                assert pd_doc.Save.call_count == 0  # Not saved when save_changes=False
                
            # Test with save changes flag
            pd_doc.Save.reset_mock()
            
            with patch("adobe_auto.pythoncom.CoUninitialize"):
                close_pdf(av_doc, pd_doc, save_changes=True)
                
                assert pd_doc.Save.call_count >= 1  # Should be saved when save_changes=True
            
        except Exception as e:
            pytest.fail(f"close_pdf raised unexpected exception: {e}")
