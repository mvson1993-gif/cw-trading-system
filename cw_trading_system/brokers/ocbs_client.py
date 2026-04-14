# brokers/ocbs_client.py

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .ocbs_adapter import OCBSAdapterTemplate
from .ocbs_sandbox import OCBSSandboxContract
from ..config.settings import BROKER_CONFIG
from ..utils.logging import get_logger
from ..errors import BrokerError

logger = get_logger(__name__)


class OCBSAPIError(BrokerError):
    """OCBS API error."""
    pass


class OCBSAuthError(OCBSAPIError):
    """OCBS authentication error."""
    pass


class OCBSClient:
    """OCBS (Order and Confirmation Booking System) API client."""

    def __init__(self, adapter: Optional[OCBSAdapterTemplate] = None, sandbox: Optional[OCBSSandboxContract] = None):
        self.base_url = BROKER_CONFIG.ocbs_base_url
        self.api_key = BROKER_CONFIG.ocbs_api_key
        self.api_secret = BROKER_CONFIG.ocbs_api_secret
        self.timeout = BROKER_CONFIG.ocbs_timeout
        self.session = requests.Session()
        self.adapter = adapter or OCBSAdapterTemplate()

        sandbox_flag = getattr(BROKER_CONFIG, "ocbs_sandbox_mode", False)
        if isinstance(sandbox_flag, str):
            self.sandbox_mode = sandbox_flag.lower() == "true"
        elif isinstance(sandbox_flag, bool):
            self.sandbox_mode = sandbox_flag
        else:
            self.sandbox_mode = False

        self.sandbox = sandbox or (OCBSSandboxContract() if self.sandbox_mode else None)
        self._last_auth_time = None
        self._auth_token = None
        self._auth_expiry = None

    def _authenticate(self) -> str:
        """Authenticate with OCBS API and get access token."""
        if self._auth_token and self._auth_expiry and datetime.now() < self._auth_expiry:
            return self._auth_token

        try:
            auth_request = self.adapter.build_auth_request(self.api_key, self.api_secret)
            self.session.headers.update(auth_request.get("headers", {}))

            if self.sandbox_mode and self.sandbox is not None:
                raw_auth_response = self.sandbox.handle_request(
                    auth_request["method"],
                    auth_request["endpoint"],
                    **self._extract_request_kwargs(auth_request)
                )
            else:
                auth_url = f"{self.base_url}{auth_request['endpoint']}"
                response = self.session.post(
                    auth_url,
                    json=auth_request.get("json"),
                    timeout=self.timeout
                )
                response.raise_for_status()
                raw_auth_response = response.json()

            auth_response = self.adapter.parse_auth_response(raw_auth_response)
            self._auth_token = auth_response.get("access_token")
            # Assume token expires in 1 hour unless the broker response says otherwise
            expiry_seconds = int(auth_response.get("expires_in", 3600) or 3600)
            self._auth_expiry = datetime.now() + timedelta(seconds=expiry_seconds)
            self._last_auth_time = datetime.now()

            # Set authorization header for future requests
            self.session.headers.update({
                "Authorization": f"Bearer {self._auth_token}"
            })

            logger.info("Successfully authenticated with OCBS API")
            return self._auth_token

        except requests.exceptions.RequestException as e:
            logger.error(f"OCBS authentication failed: {e}")
            raise OCBSAuthError(f"Authentication failed: {e}")
        except Exception as e:
            # Catch unexpected errors and wrap in domain-specific exception
            logger.exception(f"OCBS authentication failed with unexpected error: {e}")
            raise OCBSAuthError(f"Authentication failed: {e}") from e

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to OCBS API."""
        if not BROKER_CONFIG.ocbs_enabled:
            raise OCBSAPIError("OCBS integration is disabled")

        self._authenticate()

        if self.sandbox_mode and self.sandbox is not None:
            return self.sandbox.handle_request(method, endpoint, **kwargs)

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                # Token might be expired, try to re-authenticate once
                logger.warning("Token expired, re-authenticating")
                self._auth_token = None
                self._authenticate()
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response.json()
            else:
                logger.exception(f"OCBS API error: {e}")
                raise OCBSAPIError(f"API request failed: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"OCBS request failed: {e}")
            raise OCBSAPIError(f"Request failed: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in OCBS request: {e}")
            raise OCBSAPIError(f"Request failed: {e}") from e

    def _extract_request_kwargs(self, request_template: Dict[str, Any]) -> Dict[str, Any]:
        """Extract supported request kwargs from an adapter template."""
        kwargs = {}
        for key in ("json", "data", "params"):
            value = request_template.get(key)
            if value not in (None, {}):
                kwargs[key] = value
        return kwargs

    def get_account_positions(self) -> List[Dict[str, Any]]:
        """Get current account positions from OCBS."""
        try:
            request_template = self.adapter.build_positions_request()
            response = self._make_request(
                request_template["method"],
                request_template["endpoint"],
                **self._extract_request_kwargs(request_template)
            )
            positions = self.adapter.parse_positions_response(response)
            logger.info(f"Retrieved {len(positions)} positions from OCBS")
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions from OCBS: {e}")
            raise

    def get_account_trades(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get account trades from OCBS within date range."""
        params = {}
        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")

        try:
            request_template = self.adapter.build_trades_request(params=params)
            response = self._make_request(
                request_template["method"],
                request_template["endpoint"],
                **self._extract_request_kwargs(request_template)
            )
            trades = self.adapter.parse_trades_response(response)
            logger.info(f"Retrieved {len(trades)} trades from OCBS")
            return trades
        except Exception as e:
            logger.error(f"Failed to get trades from OCBS: {e}")
            raise

    def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order through OCBS."""
        required_fields = ["symbol", "side", "quantity", "order_type"]
        for field in required_fields:
            if field not in order_data:
                raise ValueError(f"Missing required field: {field}")

        try:
            request_template = self.adapter.build_order_request(order_data)
            response = self._make_request(
                request_template["method"],
                request_template["endpoint"],
                **self._extract_request_kwargs(request_template)
            )
            normalized = self.adapter.parse_order_response(response)
            order_id = normalized.get("order_id")
            logger.info(f"Placed order {order_id} for {order_data['symbol']}")
            return normalized
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from OCBS."""
        try:
            request_template = self.adapter.build_order_status_request(order_id)
            response = self._make_request(
                request_template["method"],
                request_template["endpoint"],
                **self._extract_request_kwargs(request_template)
            )
            return self.adapter.parse_order_status_response(response)
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order through OCBS."""
        try:
            request_template = self.adapter.build_cancel_order_request(order_id)
            response = self._make_request(
                request_template["method"],
                request_template["endpoint"],
                **self._extract_request_kwargs(request_template)
            )
            normalized = self.adapter.parse_cancel_order_response(response)
            logger.info(f"Cancelled order {order_id}")
            return normalized
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance from OCBS."""
        try:
            request_template = self.adapter.build_balance_request()
            response = self._make_request(
                request_template["method"],
                request_template["endpoint"],
                **self._extract_request_kwargs(request_template)
            )
            return self.adapter.parse_balance_response(response)
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            raise


# Global instance
ocbs_client = OCBSClient()