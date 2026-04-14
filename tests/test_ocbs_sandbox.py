from unittest.mock import patch

from cw_trading_system.brokers.ocbs_client import OCBSClient
from cw_trading_system.brokers.ocbs_sandbox import OCBSSandboxContract


def test_sandbox_contract_supports_auth_and_order_lifecycle():
    sandbox = OCBSSandboxContract()

    auth = sandbox.handle_request(
        "POST",
        "/auth/login",
        json={"api_key": "demo-key", "api_secret": "demo-secret"},
    )
    assert "access_token" in auth

    created = sandbox.handle_request(
        "POST",
        "/orders",
        json={
            "symbol": "HPG24001",
            "side": "buy",
            "quantity": 100000,
            "order_type": "limit",
            "price": 1.25,
        },
    )
    assert created["status"] == "accepted"

    status = sandbox.handle_request("GET", f"/orders/{created['order_id']}")
    assert status["order_id"] == created["order_id"]

    cancelled = sandbox.handle_request("DELETE", f"/orders/{created['order_id']}")
    assert cancelled["status"] == "cancelled"


@patch("cw_trading_system.brokers.ocbs_client.BROKER_CONFIG")
def test_ocbs_client_can_run_against_sandbox_mode(mock_config):
    mock_config.ocbs_enabled = True
    mock_config.ocbs_sandbox_mode = True
    mock_config.ocbs_base_url = "https://sandbox.ocbs.local"
    mock_config.ocbs_timeout = 30
    mock_config.ocbs_api_key = "demo-key"
    mock_config.ocbs_api_secret = "demo-secret"

    client = OCBSClient()
    result = client.place_order(
        {
            "symbol": "HPG24001",
            "side": "sell",
            "quantity": 50000,
            "order_type": "limit",
            "price": 1.30,
        }
    )

    assert result["status"] == "accepted"
    assert result["order_id"].startswith("SANDBOX-")
