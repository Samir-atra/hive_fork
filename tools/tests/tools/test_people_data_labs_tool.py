"""Tests for People Data Labs tool."""

from unittest.mock import MagicMock, patch

from aden_tools.credentials.people_data_labs import PEOPLE_DATA_LABS_CREDENTIALS


def test_pdl_credentials():
    """Test that PDL credentials are set up correctly."""
    spec = PEOPLE_DATA_LABS_CREDENTIALS["pdl_api_key"]
    assert spec.env_var == "PDL_API_KEY"
    assert len(spec.tools) == 4
    assert "enrich_person_pdl" in spec.tools


@patch("aden_tools.tools.people_data_labs_tool.people_data_labs_tool.httpx.get")
def test_pdl_enrich_person(mock_get):
    """Test person enrichment."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"id": "123", "full_name": "Test Person"}}
    mock_get.return_value = mock_response

    with patch.dict("os.environ", {"PDL_API_KEY": "test_key"}):
        from aden_tools.tools.people_data_labs_tool.people_data_labs_tool import pdl_enrich_person

        result = pdl_enrich_person(email="test@example.com")
        assert "data" in result
        assert result["data"]["full_name"] == "Test Person"


@patch("aden_tools.tools.people_data_labs_tool.people_data_labs_tool.httpx.get")
def test_pdl_enrich_company(mock_get):
    """Test company enrichment."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"name": "Test Company"}
    mock_get.return_value = mock_response

    with patch.dict("os.environ", {"PDL_API_KEY": "test_key"}):
        from aden_tools.tools.people_data_labs_tool.people_data_labs_tool import pdl_enrich_company

        result = pdl_enrich_company(website="example.com")
        assert result["name"] == "Test Company"


@patch("aden_tools.tools.people_data_labs_tool.people_data_labs_tool.httpx.get")
def test_pdl_search_persons(mock_get):
    """Test person search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "123"}]}
    mock_get.return_value = mock_response

    with patch.dict("os.environ", {"PDL_API_KEY": "test_key"}):
        from aden_tools.tools.people_data_labs_tool.people_data_labs_tool import pdl_search_persons

        result = pdl_search_persons(query="test query")
        assert len(result["data"]) == 1


@patch("aden_tools.tools.people_data_labs_tool.people_data_labs_tool.httpx.get")
def test_pdl_search_companies(mock_get):
    """Test company search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"name": "Test Co"}]}
    mock_get.return_value = mock_response

    with patch.dict("os.environ", {"PDL_API_KEY": "test_key"}):
        from aden_tools.tools.people_data_labs_tool.people_data_labs_tool import (
            pdl_search_companies,
        )

        result = pdl_search_companies(sql_query="SELECT * FROM test")
        assert len(result["data"]) == 1
