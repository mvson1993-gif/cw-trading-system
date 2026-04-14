# tests/test_ocbs_client.py

import pytest
from unittest.mock import patch, MagicMock
from cw_trading_system.brokers.ocbs_client import OCBSClient, OCBSAPIError, OCBSAuthError


@pytest.fixture
def ocbs_client():
    return OCBSClient()


@patch('cw_trading_system.brokers.ocbs_client.BROKER_CONFIG')
def test_ocbs_client_init(mock_config):
    mock_config.ocbs_enabled = True
    mock_config.ocbs_base_url = "https://api.test.com"
    mock_config.ocbs_api_key = "test_key"
    mock_config.ocbs_api_secret = "test_secret"
    mock_config.ocbs_timeout = 30

    client = OCBSClient()
    assert client.base_url == "https://api.test.com"
    assert client.api_key == "test_key"
    assert client.api_secret == "test_secret"
    assert client.timeout == 30


@patch('cw_trading_system.brokers.ocbs_client.BROKER_CONFIG')
@patch('cw_trading_system.brokers.ocbs_client.requests.Session')
def test_authenticate_success(mock_session, mock_config):
    mock_config.ocbs_enabled = True
    mock_config.ocbs_base_url = "https://api.ocbs.com"
    mock_config.ocbs_timeout = 30
    mock_config.ocbs_api_key = "test_key"
    mock_config.ocbs_api_secret = "test_secret"

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "test_token"}
    mock_response.raise_for_status.return_value = None

    mock_session_instance = MagicMock()
    mock_session_instance.headers = {}
    mock_session_instance.post.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = OCBSClient()
    token = client._authenticate()

    assert token == "test_token"
    mock_session_instance.post.assert_called_once()
    assert client.session.headers.get("Authorization") == "Bearer test_token"


@patch('cw_trading_system.brokers.ocbs_client.BROKER_CONFIG')
@patch('cw_trading_system.brokers.ocbs_client.requests.Session')
def test_authenticate_failure(mock_session, mock_config):
    mock_config.ocbs_enabled = True
    mock_config.ocbs_base_url = "https://api.ocbs.com"
    mock_config.ocbs_timeout = 30
    mock_config.ocbs_api_key = "test_key"
    mock_config.ocbs_api_secret = "test_secret"

    mock_session_instance = MagicMock()
    mock_session_instance.headers = {}
    mock_session_instance.post.side_effect = Exception("Connection failed")
    mock_session.return_value = mock_session_instance

    client = OCBSClient()

    with pytest.raises(OCBSAuthError):
        client._authenticate()


@patch('cw_trading_system.brokers.ocbs_client.BROKER_CONFIG')
def test_make_request_disabled(mock_config):
    mock_config.ocbs_enabled = False

    client = OCBSClient()

    with pytest.raises(OCBSAPIError, match="OCBS integration is disabled"):
        client._make_request("GET", "/test")


@patch('cw_trading_system.brokers.ocbs_client.BROKER_CONFIG')
@patch.object(OCBSClient, '_authenticate')
@patch('cw_trading_system.brokers.ocbs_client.requests.Session')
def test_make_request_success(mock_session, mock_auth, mock_config):
    mock_config.ocbs_enabled = True
    mock_config.ocbs_base_url = "https://api.ocbs.com"
    mock_config.ocbs_timeout = 30

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_response.raise_for_status.return_value = None

    mock_session_instance = MagicMock()
    mock_session_instance.headers = {}
    mock_session_instance.request.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = OCBSClient()
    result = client._make_request("GET", "/test")

    assert result == {"data": "test"}
    mock_session_instance.request.assert_called_once_with("GET", "https://api.ocbs.com/test", timeout=30)


@patch('cw_trading_system.brokers.ocbs_client.BROKER_CONFIG')
@patch.object(OCBSClient, '_authenticate')
@patch('cw_trading_system.brokers.ocbs_client.requests.Session')
def test_get_account_positions(mock_session, mock_auth, mock_config):
    mock_config.ocbs_enabled = True

    mock_response = MagicMock()
    mock_response.json.return_value = {"positions": [{"symbol": "AAPL", "quantity": 100}]}
    mock_response.raise_for_status.return_value = None

    mock_session_instance = MagicMock()
    mock_session_instance.request.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = OCBSClient()
    positions = client.get_account_positions()

    assert positions == [{"symbol": "AAPL", "quantity": 100}]


@patch('cw_trading_system.brokers.ocbs_client.BROKER_CONFIG')
@patch.object(OCBSClient, '_authenticate')
@patch('cw_trading_system.brokers.ocbs_client.requests.Session')
def test_place_order(mock_session, mock_auth, mock_config):
    mock_config.ocbs_enabled = True
    mock_config.ocbs_base_url = "https://api.ocbs.com"
    mock_config.ocbs_timeout = 30

    mock_response = MagicMock()
    mock_response.json.return_value = {"order_id": "12345", "status": "placed"}
    mock_response.raise_for_status.return_value = None

    mock_session_instance = MagicMock()
    mock_session_instance.headers = {}
    mock_session_instance.request.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = OCBSClient()
    order_data = {"symbol": "AAPL", "side": "buy", "quantity": 100, "order_type": "market"}
    result = client.place_order(order_data)

    assert result == {"order_id": "12345", "status": "placed"}
    mock_session_instance.request.assert_called_with("POST", "https://api.ocbs.com/orders", json=order_data, timeout=30)