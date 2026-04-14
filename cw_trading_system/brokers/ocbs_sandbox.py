from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


class OCBSSandboxContract:
    """In-memory OCBS sandbox contract for local development and integration testing.

    This mock implements the same high-level endpoints expected by `OCBSClient`.
    It lets the trading workflow run before the real OCBS API is available.
    """

    def __init__(self):
        self._token_counter = 0
        self._order_counter = 0
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.positions: List[Dict[str, Any]] = [
            {
                "symbol": "HPG.VN",
                "quantity": 250000,
                "avg_price": 31.2,
                "market_value": 7_800_000.0,
            }
        ]
        self.trades: List[Dict[str, Any]] = []
        self.balance: Dict[str, Any] = {
            "account_id": "SANDBOX-001",
            "currency": "VND",
            "cash_available": 10_000_000_000.0,
            "buying_power": 25_000_000_000.0,
            "margin_used": 0.0,
        }

    def handle_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        method = method.upper().strip()
        payload = kwargs.get("json") or kwargs.get("data") or {}
        params = kwargs.get("params") or {}

        if method == "POST" and endpoint == "/auth/login":
            return self._authenticate(payload)
        if method == "GET" and endpoint == "/positions":
            return {"positions": list(self.positions), "environment": "sandbox"}
        if method == "GET" and endpoint == "/trades":
            return {"trades": list(self.trades), "params": params, "environment": "sandbox"}
        if method == "GET" and endpoint == "/balance":
            return {**self.balance, "environment": "sandbox"}
        if method == "POST" and endpoint == "/orders":
            return self._place_order(payload)
        if endpoint.startswith("/orders/"):
            order_id = endpoint.split("/orders/", 1)[1]
            if method == "GET":
                return self._get_order_status(order_id)
            if method == "DELETE":
                return self._cancel_order(order_id)

        raise ValueError(f"Unsupported sandbox route: {method} {endpoint}")

    def _authenticate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._token_counter += 1
        return {
            "access_token": f"sandbox-token-{self._token_counter:04d}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "environment": "sandbox",
            "received_api_key": payload.get("api_key", ""),
        }

    def _place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["symbol", "side", "quantity", "order_type"]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"Missing required order fields: {', '.join(missing)}")

        self._order_counter += 1
        order_id = f"SANDBOX-{self._order_counter:06d}"
        now = datetime.now(UTC).isoformat(timespec="seconds")
        order = {
            "order_id": order_id,
            "symbol": payload["symbol"],
            "side": str(payload["side"]).lower(),
            "quantity": int(payload["quantity"]),
            "price": payload.get("price"),
            "order_type": payload["order_type"],
            "status": "accepted",
            "execution_price": payload.get("price"),
            "filled_quantity": 0,
            "created_at": now,
            "environment": "sandbox",
        }
        self.orders[order_id] = order
        self.trades.append(
            {
                "trade_id": f"TRD-{self._order_counter:06d}",
                "order_id": order_id,
                "symbol": order["symbol"],
                "side": order["side"],
                "quantity": order["quantity"],
                "price": order["price"],
                "timestamp": now,
                "status": order["status"],
            }
        )
        return order

    def _get_order_status(self, order_id: str) -> Dict[str, Any]:
        if order_id not in self.orders:
            return {
                "order_id": order_id,
                "status": "not_found",
                "environment": "sandbox",
            }
        return dict(self.orders[order_id])

    def _cancel_order(self, order_id: str) -> Dict[str, Any]:
        order = self.orders.get(order_id)
        if not order:
            return {
                "order_id": order_id,
                "status": "not_found",
                "environment": "sandbox",
            }

        order["status"] = "cancelled"
        order["cancelled_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        return dict(order)
