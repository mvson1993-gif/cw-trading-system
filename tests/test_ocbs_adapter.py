from cw_trading_system.brokers.ocbs_adapter import OCBSAdapterTemplate


def test_build_auth_request_uses_template_defaults():
    adapter = OCBSAdapterTemplate()

    request = adapter.build_auth_request("test_key", "test_secret")

    assert request["method"] == "POST"
    assert request["endpoint"] == "/auth/login"
    assert request["json"] == {
        "api_key": "test_key",
        "api_secret": "test_secret",
    }


def test_build_order_request_supports_field_mapping():
    adapter = OCBSAdapterTemplate(
        order_field_map={
            "symbol": "instrument",
            "side": "action",
            "quantity": "qty",
            "order_type": "type",
            "price": "limit_price",
        }
    )

    request = adapter.build_order_request(
        {
            "symbol": "HPG24001",
            "side": "buy",
            "quantity": 100000,
            "order_type": "limit",
            "price": 1.25,
            "time_in_force": "day",
        }
    )

    assert request["endpoint"] == "/orders"
    assert request["json"]["instrument"] == "HPG24001"
    assert request["json"]["action"] == "buy"
    assert request["json"]["qty"] == 100000
    assert request["json"]["type"] == "limit"
    assert request["json"]["limit_price"] == 1.25


def test_parse_order_response_normalizes_common_ocbs_fields():
    adapter = OCBSAdapterTemplate()

    parsed = adapter.parse_order_response(
        {
            "id": "ORD-123",
            "state": "accepted",
            "avgPrice": 1.23,
            "filledQty": 50000,
        }
    )

    assert parsed["order_id"] == "ORD-123"
    assert parsed["status"] == "accepted"
    assert parsed["execution_price"] == 1.23
    assert parsed["filled_quantity"] == 50000
