from cw_trading_system.brokers.ocbs_mock_sandbox import OCBSSandboxMock, load_ocbs_sandbox_spec


def test_load_ocbs_sandbox_spec_contains_orders_endpoint():
    spec = load_ocbs_sandbox_spec()

    assert spec["info"]["title"] == "OCBS Mock Sandbox Contract"
    assert "/orders" in spec["paths"]


def test_mock_sandbox_order_lifecycle():
    sandbox = OCBSSandboxMock()

    auth = sandbox.handle_request(
        "POST",
        "/auth/login",
        json={"api_key": "sandbox_key", "api_secret": "sandbox_secret"},
    )
    assert auth["access_token"].startswith("sandbox-")

    order = sandbox.handle_request(
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
    order_id = order["order_id"]
    assert order["status"] == "accepted"

    fetched = sandbox.handle_request("GET", f"/orders/{order_id}")
    assert fetched["order_id"] == order_id

    cancelled = sandbox.handle_request("DELETE", f"/orders/{order_id}")
    assert cancelled["status"] == "cancelled"
