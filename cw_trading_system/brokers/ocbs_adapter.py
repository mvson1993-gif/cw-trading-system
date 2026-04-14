from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional


@dataclass
class OCBSEndpointConfig:
    """Default endpoint template for OCBS API integration.

    Update these values when the real OCBS specification is available.
    """

    auth: str = "/auth/login"
    positions: str = "/positions"
    trades: str = "/trades"
    orders: str = "/orders"
    balance: str = "/balance"


class OCBSAdapterTemplate:
    """Template adapter to translate internal order data to the future OCBS schema.

    The real OCBS API details can be plugged in later by overriding endpoint names,
    request field mappings, and response aliases without changing the rest of the
    trading engines.
    """

    def __init__(
        self,
        endpoints: Optional[OCBSEndpointConfig] = None,
        auth_field_map: Optional[Dict[str, str]] = None,
        order_field_map: Optional[Dict[str, str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.endpoints = endpoints or OCBSEndpointConfig()
        self.auth_field_map = auth_field_map or {
            "api_key": "api_key",
            "api_secret": "api_secret",
        }
        self.order_field_map = order_field_map or {
            "symbol": "symbol",
            "side": "side",
            "quantity": "quantity",
            "order_type": "order_type",
            "price": "price",
            "time_in_force": "time_in_force",
        }
        self.default_headers = default_headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def build_auth_request(self, api_key: str, api_secret: str) -> Dict[str, Any]:
        payload = {
            self.auth_field_map["api_key"]: api_key,
            self.auth_field_map["api_secret"]: api_secret,
        }
        return {
            "method": "POST",
            "endpoint": self.endpoints.auth,
            "json": payload,
            "headers": dict(self.default_headers),
        }

    def parse_auth_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        token = self._pick_first(response_data, ["access_token", "token", "auth_token", "jwt"])
        expires_in = self._pick_first(response_data, ["expires_in", "expiresIn", "ttl"], default=3600)

        normalized = dict(response_data)
        if token is not None:
            normalized["access_token"] = token
        normalized.setdefault("expires_in", expires_in)
        return normalized

    def build_order_request(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._map_payload(order_data, self.order_field_map)
        return {
            "method": "POST",
            "endpoint": self.endpoints.orders,
            "json": payload,
            "headers": dict(self.default_headers),
        }

    def parse_order_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(response_data)
        self._inject_if_missing(normalized, "order_id", self._pick_first(response_data, ["order_id", "id", "orderNo"]))
        self._inject_if_missing(normalized, "status", self._pick_first(response_data, ["status", "state", "orderStatus"]))
        self._inject_if_missing(normalized, "execution_price", self._pick_first(response_data, ["execution_price", "avgPrice", "average_price", "price"]))
        self._inject_if_missing(normalized, "filled_quantity", self._pick_first(response_data, ["filled_quantity", "filledQty", "executed_quantity"]))
        return normalized

    def build_positions_request(self) -> Dict[str, Any]:
        return {
            "method": "GET",
            "endpoint": self.endpoints.positions,
            "headers": dict(self.default_headers),
        }

    def parse_positions_response(self, response_data: Dict[str, Any]) -> list[Dict[str, Any]]:
        if isinstance(response_data, list):
            return response_data
        positions = self._pick_first(response_data, ["positions", "data", "items"], default=[])
        return positions if isinstance(positions, list) else []

    def build_trades_request(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "method": "GET",
            "endpoint": self.endpoints.trades,
            "params": params or {},
            "headers": dict(self.default_headers),
        }

    def parse_trades_response(self, response_data: Dict[str, Any]) -> list[Dict[str, Any]]:
        if isinstance(response_data, list):
            return response_data
        trades = self._pick_first(response_data, ["trades", "data", "items"], default=[])
        return trades if isinstance(trades, list) else []

    def build_order_status_request(self, order_id: str) -> Dict[str, Any]:
        return {
            "method": "GET",
            "endpoint": f"{self.endpoints.orders}/{order_id}",
            "headers": dict(self.default_headers),
        }

    def parse_order_status_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.parse_order_response(response_data)

    def build_cancel_order_request(self, order_id: str) -> Dict[str, Any]:
        return {
            "method": "DELETE",
            "endpoint": f"{self.endpoints.orders}/{order_id}",
            "headers": dict(self.default_headers),
        }

    def parse_cancel_order_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(response_data)
        self._inject_if_missing(normalized, "status", self._pick_first(response_data, ["status", "state"], default="cancelled"))
        return normalized

    def build_balance_request(self) -> Dict[str, Any]:
        return {
            "method": "GET",
            "endpoint": self.endpoints.balance,
            "headers": dict(self.default_headers),
        }

    def parse_balance_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        return dict(response_data)

    def _map_payload(self, payload: Dict[str, Any], field_map: Dict[str, str]) -> Dict[str, Any]:
        mapped = {}
        for source_key, value in payload.items():
            target_key = field_map.get(source_key, source_key)
            mapped[target_key] = value
        return mapped

    def _pick_first(self, payload: Dict[str, Any], aliases: Iterable[str], default: Any = None) -> Any:
        for alias in aliases:
            if alias in payload and payload[alias] is not None:
                return payload[alias]
        return default

    def _inject_if_missing(self, payload: Dict[str, Any], key: str, value: Any) -> None:
        if key not in payload and value is not None:
            payload[key] = value
