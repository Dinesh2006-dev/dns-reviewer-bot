import sys
import os
import pytest
from unittest import mock

# Add agent folder to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agent')))

import llm_analyzer

@pytest.fixture
def mock_change():
    return {
        "type": "added",
        "raw": "www 3600 IN A 93.184.216.34",
        "record": {
            "name": "www",
            "ttl": 3600,
            "rclass": "IN",
            "rtype": "A",
            "value": "93.184.216.34"
        }
    }

def test_llm_analyzer_ollama_success(mock_change):
    # Setup environment: OPENROUTER_API_KEY is None or empty
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
        # Reload key value in module
        llm_analyzer.OPENROUTER_API_KEY = None
        
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "response": '{"risk_level": "safe", "explanation": "Standard A record.", "suggestion": null}'
        }
        mock_response.raise_for_status.return_value = None
        
        with mock.patch("requests.post", return_value=mock_response) as mock_post:
            result = llm_analyzer.analyze_with_llm(mock_change)
            
            # Verify POST was called with Ollama parameters
            mock_post.assert_called_once()
            called_url, called_kwargs = mock_post.call_args
            assert called_url[0] == llm_analyzer.OLLAMA_URL
            assert called_kwargs["json"]["model"] == llm_analyzer.MODEL
            
            # Verify structure of result
            assert result["risk_level"] == "safe"
            assert result["explanation"] == "Standard A record."
            assert result["change"] == mock_change["raw"]

def test_llm_analyzer_openrouter_success(mock_change):
    # Setup environment: OPENROUTER_API_KEY is set
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake_openrouter_key"}):
        llm_analyzer.OPENROUTER_API_KEY = "fake_openrouter_key"
        
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"risk_level": "safe", "explanation": "Cloud analysis.", "suggestion": null}'
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        with mock.patch("requests.post", return_value=mock_response) as mock_post:
            result = llm_analyzer.analyze_with_llm(mock_change)
            
            # Verify POST was called with OpenRouter parameters
            mock_post.assert_called_once()
            called_url, called_kwargs = mock_post.call_args
            assert called_url[0] == "https://openrouter.ai/api/v1/chat/completions"
            assert called_kwargs["headers"]["Authorization"] == "Bearer fake_openrouter_key"
            assert called_kwargs["json"]["model"] == llm_analyzer.OPENROUTER_MODEL
            
            # Verify structure of result
            assert result["risk_level"] == "safe"
            assert result["explanation"] == "Cloud analysis."
            assert result["change"] == mock_change["raw"]

def test_llm_analyzer_fallback_on_error(mock_change):
    # Setup environment: OPENROUTER_API_KEY is set
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake_openrouter_key"}):
        llm_analyzer.OPENROUTER_API_KEY = "fake_openrouter_key"
        
        # Simulate connection error
        with mock.patch("requests.post", side_effect=Exception("Connection refused")):
            result = llm_analyzer.analyze_with_llm(mock_change)
            
            # Verify graceful fallback response
            assert result["risk_level"] == "warning"
            assert "OpenRouter" in result["explanation"]
            assert "Connection refused" in result["explanation"]
            assert result["change"] == mock_change["raw"]
