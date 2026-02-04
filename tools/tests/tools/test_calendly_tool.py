import pytest
from unittest.mock import Mock, patch
import httpx
from aden_tools.tools.calendly_tool import (
    get_calendly_headers,
    get_current_user,
    list_event_types,
    create_scheduling_link
)

@pytest.fixture
def mock_api_key():
    return "test-api-key"

@pytest.fixture
def mock_user_uri():
    return "https://api.calendly.com/users/USER_UUID"

@pytest.fixture
def mock_event_type_uri():
    return "https://api.calendly.com/event_types/EVENT_UUID"

def test_get_calendly_headers(mock_api_key):
    headers = get_calendly_headers(mock_api_key)
    assert headers["Authorization"] == f"Bearer {mock_api_key}"
    assert headers["Content-Type"] == "application/json"

@patch('httpx.Client.get')
def test_get_current_user(mock_get, mock_api_key, mock_user_uri):
    mock_response = Mock()
    mock_response.json.return_value = {
        "resource": {
            "uri": mock_user_uri,
            "name": "Test User"
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    user = get_current_user(mock_api_key)
    
    assert user["uri"] == mock_user_uri
    mock_get.assert_called_once_with(
        "https://api.calendly.com/users/me",
        headers={"Authorization": f"Bearer {mock_api_key}", "Content-Type": "application/json"}
    )

@patch('httpx.Client.get')
def test_list_event_types(mock_get, mock_api_key, mock_user_uri):
    mock_response = Mock()
    mock_response.json.return_value = {
        "collection": [
            {"uri": "uri1", "name": "Event 1"},
            {"uri": "uri2", "name": "Event 2"}
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    # Test with user_uri provided
    event_types = list_event_types(mock_api_key, user_uri=mock_user_uri)
    
    assert len(event_types) == 2
    mock_get.assert_called_once_with(
        "https://api.calendly.com/event_types",
        headers=get_calendly_headers(mock_api_key),
        params={"user": mock_user_uri}
    )

@patch('aden_tools.tools.calendly_tool.get_current_user')
@patch('httpx.Client.get')
def test_list_event_types_no_user_uri(mock_get, mock_get_user, mock_api_key, mock_user_uri):
    # Mock getting current user
    mock_get_user.return_value = {"uri": mock_user_uri}
    
    # Mock list response
    mock_response = Mock()
    mock_response.json.return_value = {"collection": []}
    mock_get.return_value = mock_response

    list_event_types(mock_api_key)
    
    # Verify get_current_user was called
    mock_get_user.assert_called_once_with(mock_api_key)
    
    # Verify list event types called with fetched user uri
    mock_get.assert_called_once()
    assert mock_get.call_args[1]['params']['user'] == mock_user_uri

@patch('httpx.Client.post')
def test_create_scheduling_link(mock_post, mock_api_key, mock_event_type_uri):
    expected_link = "https://calendly.com/booking/link"
    mock_response = Mock()
    mock_response.json.return_value = {
        "resource": {
            "booking_url": expected_link
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    link = create_scheduling_link(mock_api_key, mock_event_type_uri)
    
    assert link == expected_link
    mock_post.assert_called_once_with(
        "https://api.calendly.com/scheduling_links",
        headers=get_calendly_headers(mock_api_key),
        json={
            "max_event_count": 1,
            "owner": mock_event_type_uri,
            "owner_type": "EventType"
        }
    )
