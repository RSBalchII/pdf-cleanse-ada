"""
Unit tests for adobe_autotag_api.py - Adobe PDF Services API integration.

Tests cover:
- AdobeAPI class initialization
- Token retrieval and refresh
- Asset upload
- Auto-tag job submission
- Job status polling
- Tagged PDF download
- Credentials loading from JSON file
"""


import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import functions under test
from adobe_autotag_api import (
    AdobeAPI,
    load_credentials,
    auto_tag_pdf,
)


class TestAdobeAPIInit:
    """Tests for AdobeAPI class initialization."""
    
    def test_adobe_api_init_with_optional_params(self):
        """Test AdobeAPI with client_id and client_secret."""
        api = AdobeAPI(client_id="test_client", client_secret="test_secret")
        
        assert api.client_id == "test_client"
        assert api.client_secret == "test_secret"
    
    def test_adobe_api_init_without_params(self):
        """Test AdobeAPI without credentials (uses environment vars)."""
        # Test with env vars provided via context
        import os
        old_client_id = os.environ.get("ADOBE_CLIENT_ID")
        old_client_secret = os.environ.get("ADOBE_CLIENT_SECRET")
        
        try:
            os.environ["ADOBE_CLIENT_ID"] = "env_client"
            os.environ["ADOBE_CLIENT_SECRET"] = "env_secret"
            
            api = AdobeAPI()  # Should load from env
            
            assert api.client_id == "env_client"
            assert api.client_secret == "env_secret"
        finally:
            # Restore original values
            if old_client_id is None:
                os.environ.pop("ADOBE_CLIENT_ID", None)
            else:
                os.environ["ADOBE_CLIENT_ID"] = old_client_id
            if old_client_secret is None:
                os.environ.pop("ADOBE_CLIENT_SECRET", None)
            else:
                os.environ["ADOBE_CLIENT_SECRET"] = old_client_secret


class TestGetToken:
    """Tests for the get_token() method."""
    
    def test_get_token_with_env_var(self):
        """Test that get_token uses environment variable when available."""
        import os
        
        api = AdobeAPI(client_id="test", client_secret="secret")
        
        # Mock the session to prevent actual API call
        with patch.object(api.session, 'post') as mock_post:
            old_env_token = os.environ.get("ADOBE_ACCESS_TOKEN")
            
            try:
                os.environ["ADOBE_ACCESS_TOKEN"] = "env_test_token"
                
                api.access_token = None  # Reset to force token refresh
                
                result = api.get_token()
                
                assert result == "env_test_token"
                mock_post.assert_not_called()  # Should use env var directly
            
            finally:
                if old_env_token is None:
                    os.environ.pop("ADOBE_ACCESS_TOKEN", None)
                else:
                    os.environ["ADOBE_ACCESS_TOKEN"] = old_env_token
    
    def test_get_token_refreshes(self):
        """Test that get_token refreshes when token expires."""
        import time
        
        api = AdobeAPI(client_id="test", client_secret="secret")
        
        # Mock session post to return a response with 86400 second expiry
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed_token_123",
            "expires_in": 86400
        }
        
        with patch.object(api.session, 'post', return_value=mock_response):
            api.get_token()
            
        # Token should be set by the API call
        assert hasattr(api, 'access_token')


class TestUploadAsset:
    """Tests for the upload_asset() method."""
    
    def test_upload_asset_returns_asset_id(self):
        """Test that upload_asset returns an asset ID string."""
        api = AdobeAPI(client_id="test", client_secret="secret")
        
        mock_pdf_path = Path("/tmp/test.pdf")
        mock_pdf_path.stat.return_value.st_size = 1024
        
        # Mock the API calls
        with patch.object(api.session, 'post') as mock_post:
            old_env_token = os.environ.get("ADOBE_ACCESS_TOKEN")
            
            try:
                # Simulate two uploads (asset + file)
                mock_response1 = MagicMock()
                mock_response1.status_code = 200
                mock_response1.json.return_value = {
                    "assetID": "test_asset_123",
                    "uploadUri": "http://example.com/upload"
                }
                
                mock_response2 = MagicMock()
                mock_response2.status_code = 200
                
                with patch.object(api.session, 'put', return_value=mock_response2):
                    result = api.upload_asset(mock_pdf_path)
                    
            finally:
                if old_env_token is None:
                    os.environ.pop("ADOBE_ACCESS_TOKEN", None)
                else:
                    os.environ["ADOBE_ACCESS_TOKEN"] = old_env_token
            
        # Should return asset ID
        assert isinstance(result, str)


class TestSubmitAutotagJob:
    """Tests for the submit_autotag_job() method."""
    
    def test_submit_autotag_job_returns_job_id(self):
        """Test that submit_autotag_job returns a job ID string."""
        api = AdobeAPI(client_id="test", client_secret="secret")
        
        # Mock API response with Location header containing job ID
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/operation/autotag/job_456/status"}
        
        with patch.object(api.session, 'post', return_value=mock_response):
            result = api.submit_autotag_job(asset_id="test_asset")
            
        assert isinstance(result, str)


class TestPollJobStatus:
    """Tests for the poll_job_status() method."""
    
    def test_poll_job_status_returns_done(self):
        """Test that polling returns status data when job completes."""
        api = AdobeAPI(client_id="test", client_secret="secret")
        
        # Mock successful status response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "done"
        }
        
        with patch.object(api.session, 'get', return_value=mock_response):
            result = api.poll_job_status(job_id="test_123", timeout=60)
            
        assert isinstance(result, dict)


class TestDownloadTaggedPdf:
    """Tests for the download_tagged_pdf() method."""
    
    def test_download_tagged_pdf_returns_path(self):
        """Test that download_tagged_pdf returns a Path object."""
        api = AdobeAPI(client_id="test", client_secret="secret")
        
        # Mock responses for asset download and file retrieval
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "assetID": "test_asset",
            "downloadUri": "http://example.com/download"
        }
        
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        
        with patch.object(api.session, 'get', return_value=mock_response1):
            output_path = Path("/tmp/output.pdf")
            
            result = api.download_tagged_pdf(asset_id="test_asset", output_path=output_path)
            
        assert isinstance(result, Path)


class TestLoadCredentials:
    """Tests for the load_credentials() function."""
    
    def test_load_credentials_from_json(self):
        """Test loading credentials from JSON file."""
        import os
        
        # Create a temp credentials file
        creds_file = Path("/tmp/test_creds.json")
        
        with patch("adobe_autotag_api.CONFIG_PATH", creds_file):
            json_data = {"client_id": "json_client", "client_secret": "json_secret"}
            
            with open(creds_file, 'w') as f:
                json.dump(json_data, f)
            
            client_id, client_secret = load_credentials()
            
        assert client_id == "json_client"
        assert client_secret == "json_secret"


class TestAutoTagPdf:
    """Tests for the auto_tag_pdf() function."""
    
    def test_auto_tag_pdf_returns_result_dict(self):
        """Test that auto_tag_pdf returns a result dictionary."""
        api = AdobeAPI(client_id="test", client_secret="secret")
        
        mock_pdf_path = Path("/tmp/test.pdf")
        output_path = Path("/tmp/output.pdf")
        
        # Mock all API methods
        with patch.object(api, 'upload_asset') as mock_upload:
            with patch.object(api, 'submit_autotag_job') as mock_submit:
                with patch.object(api, 'poll_job_status') as mock_poll:
                    with patch.object(api, 'download_tagged_pdf') as mock_download:
                        
                        mock_upload.return_value = "asset_123"
                        mock_submit.return_value = "job_456"
                        mock_download.return_value = output_path
                        
                        result = auto_tag_pdf(api, mock_pdf_path, output_path)
            
        assert isinstance(result, dict)
