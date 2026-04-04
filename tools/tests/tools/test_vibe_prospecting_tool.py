"""Tests for VibeProspecting tool."""

from unittest.mock import MagicMock, patch

from aden_tools.credentials.vibe_prospecting import VIBE_PROSPECTING_CREDENTIALS


def test_vibe_credentials():
    """Test that Vibe credentials are set up correctly."""
    spec = VIBE_PROSPECTING_CREDENTIALS["vibe_api_key"]
    assert spec.env_var == "VIBE_API_KEY"
    assert len(spec.tools) == 2
    assert "search_prospects_vibe" in spec.tools


@patch("aden_tools.tools.vibe_prospecting_tool.vibe_prospecting_tool.httpx.get")
def test_vibe_search_prospects(mock_get):
    """Test searching prospects."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"prospects": [{"id": "1", "name": "John"}]}
    mock_get.return_value = mock_response

    with patch.dict("os.environ", {"VIBE_API_KEY": "test_key"}):
        from aden_tools.tools.vibe_prospecting_tool.vibe_prospecting_tool import (
            vibe_search_prospects,
        )

        result = vibe_search_prospects(query="software engineer")
        assert "prospects" in result
        assert len(result["prospects"]) == 1


@patch("aden_tools.tools.vibe_prospecting_tool.vibe_prospecting_tool.httpx.post")
def test_vibe_generate_lead_list(mock_post):
    """Test generating a lead list."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"list_id": "list_123", "status": "processing"}
    mock_post.return_value = mock_response

    with patch.dict("os.environ", {"VIBE_API_KEY": "test_key"}):
        from aden_tools.tools.vibe_prospecting_tool.vibe_prospecting_tool import (
            vibe_generate_lead_list,
        )

        result = vibe_generate_lead_list(list_name="Engineers", criteria={"role": "Engineer"})
        assert result["list_id"] == "list_123"
