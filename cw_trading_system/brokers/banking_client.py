# brokers/banking_client.py

"""
Banking & Settlement API Framework

This module provides APIs for banking operations, settlement monitoring,
and capital management integration with Vietnamese banks.
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ..config.settings import BANKING_CONFIG
from ..utils.logging import get_logger
from ..errors import BrokerError

logger = get_logger(__name__)


class BankingError(BrokerError):
    """Banking API error."""
    pass


class BankAPIClient:
    """Base class for bank API clients."""

    def __init__(self, bank_name: str, config: Dict[str, Any]):
        self.bank_name = bank_name
        self.config = config
        self.session = requests.Session()
        self._auth_token = None
        self._token_expiry = None

    def is_enabled(self) -> bool:
        """Check if this bank API is enabled."""
        return self.config.get("enabled", False)

    def authenticate(self) -> None:
        """Authenticate with bank API. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement authenticate()")

    def get_account_balance(self) -> Optional[float]:
        """Get account balance."""
        raise NotImplementedError("Subclasses must implement get_account_balance()")

    def get_transaction_history(self, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Get transaction history."""
        raise NotImplementedError("Subclasses must implement get_transaction_history()")

    def check_settlement_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Check settlement status for a transaction."""
        raise NotImplementedError("Subclasses must implement check_settlement_status()")

    def get_margin_info(self) -> Optional[Dict[str, Any]]:
        """Get margin account information."""
        raise NotImplementedError("Subclasses must implement get_margin_info()")


class VietcombankAPI(BankAPIClient):
    """Vietcombank API client."""

    def __init__(self):
        config = BANKING_CONFIG.banks["vietcombank"]
        super().__init__("Vietcombank", config)

    def authenticate(self) -> None:
        """Authenticate with Vietcombank API."""
        if not self.is_enabled():
            return

        try:
            auth_url = f"{self.config['base_url']}/oauth/token"
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.config["api_key"],
                "client_secret": self.config["api_secret"]
            }

            response = self.session.post(auth_url, data=auth_data, timeout=30)
            response.raise_for_status()

            data = response.json()
            self._auth_token = data.get("access_token")
            self._token_expiry = datetime.now() + timedelta(hours=1)

            self.session.headers.update({"Authorization": f"Bearer {self._auth_token}"})
            logger.info("Vietcombank API authentication successful")

        except Exception as e:
            logger.error(f"Vietcombank API authentication failed: {e}")
            raise BankingError(f"Vietcombank authentication failed: {e}")

    def get_account_balance(self) -> Optional[float]:
        """Get account balance from Vietcombank."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/accounts/{self.config['account_number']}/balance"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            balance = data.get("available_balance")
            return float(balance) if balance else None

        except Exception as e:
            logger.warning(f"Failed to get Vietcombank account balance: {e}")
            return None

    def get_transaction_history(self, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Get transaction history from Vietcombank."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            params = {
                "account_number": self.config["account_number"],
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }

            url = f"{self.config['base_url']}/accounts/{self.config['account_number']}/transactions"
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            return data.get("transactions", [])

        except Exception as e:
            logger.warning(f"Failed to get Vietcombank transaction history: {e}")
            return None

    def check_settlement_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Check settlement status for a transaction."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/settlements/{transaction_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "transaction_id": transaction_id,
                "status": data.get("status"),
                "settlement_date": data.get("settlement_date"),
                "amount": data.get("amount")
            }

        except Exception as e:
            logger.warning(f"Failed to check Vietcombank settlement status for {transaction_id}: {e}")
            return None

    def get_margin_info(self) -> Optional[Dict[str, Any]]:
        """Get margin account information."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/accounts/{self.config['account_number']}/margin"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "margin_limit": data.get("margin_limit"),
                "margin_used": data.get("margin_used"),
                "margin_available": data.get("margin_available"),
                "maintenance_margin": data.get("maintenance_margin"),
                "margin_call": data.get("margin_call", False)
            }

        except Exception as e:
            logger.warning(f"Failed to get Vietcombank margin info: {e}")
            return None


class TechcombankAPI(BankAPIClient):
    """Techcombank API client."""

    def __init__(self):
        config = BANKING_CONFIG.banks["techcombank"]
        super().__init__("Techcombank", config)

    def authenticate(self) -> None:
        """Authenticate with Techcombank API."""
        if not self.is_enabled():
            return

        try:
            # Techcombank uses JWT authentication
            auth_url = f"{self.config['base_url']}/auth/login"
            auth_data = {
                "username": self.config["api_key"],  # API key as username
                "password": self.config["api_secret"]
            }

            response = self.session.post(auth_url, json=auth_data, timeout=30)
            response.raise_for_status()

            data = response.json()
            self._auth_token = data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self._auth_token}"})

            logger.info("Techcombank API authentication successful")

        except Exception as e:
            logger.error(f"Techcombank API authentication failed: {e}")
            raise BankingError(f"Techcombank authentication failed: {e}")

    def get_account_balance(self) -> Optional[float]:
        """Get account balance from Techcombank."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/account/balance"
            params = {"account": self.config["account_number"]}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            balance = data.get("balance")
            return float(balance) if balance else None

        except Exception as e:
            logger.warning(f"Failed to get Techcombank account balance: {e}")
            return None

    def get_transaction_history(self, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Get transaction history from Techcombank."""
        # TODO: Implement when API documentation is available
        logger.info("Techcombank transaction history - Framework ready")
        return None

    def check_settlement_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Check settlement status for a transaction."""
        # TODO: Implement when API documentation is available
        logger.info(f"Techcombank settlement check for {transaction_id} - Framework ready")
        return None

    def get_margin_info(self) -> Optional[Dict[str, Any]]:
        """Get margin account information."""
        # TODO: Implement when API documentation is available
        logger.info("Techcombank margin info - Framework ready")
        return None


class VietinbankAPI(BankAPIClient):
    """Vietinbank API client."""

    def __init__(self):
        config = BANKING_CONFIG.banks["vietinbank"]
        super().__init__("Vietinbank", config)

    def authenticate(self) -> None:
        """Authenticate with Vietinbank API."""
        if not self.is_enabled():
            return

        try:
            # Vietinbank uses API key authentication
            self.session.headers.update({
                "X-API-Key": self.config["api_key"],
                "X-API-Secret": self.config["api_secret"],
                "X-Account-Number": self.config["account_number"]
            })

            logger.info("Vietinbank API authentication configured")

        except Exception as e:
            logger.error(f"Vietinbank API authentication failed: {e}")
            raise BankingError(f"Vietinbank authentication failed: {e}")

    def get_account_balance(self) -> Optional[float]:
        """Get account balance from Vietinbank."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/balance"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            balance = data.get("available_balance")
            return float(balance) if balance else None

        except Exception as e:
            logger.warning(f"Failed to get Vietinbank account balance: {e}")
            return None

    def get_transaction_history(self, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Get transaction history from Vietinbank."""
        # TODO: Implement when API documentation is available
        logger.info("Vietinbank transaction history - Framework ready")
        return None

    def check_settlement_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Check settlement status for a transaction."""
        # TODO: Implement when API documentation is available
        logger.info(f"Vietinbank settlement check for {transaction_id} - Framework ready")
        return None

    def get_margin_info(self) -> Optional[Dict[str, Any]]:
        """Get margin account information."""
        # TODO: Implement when API documentation is available
        logger.info("Vietinbank margin info - Framework ready")
        return None


class SettlementMonitor:
    """Settlement monitoring and reconciliation."""

    def __init__(self):
        self.bank_clients = {
            "vietcombank": VietcombankAPI(),
            "techcombank": TechcombankAPI(),
            "vietinbank": VietinbankAPI()
        }
        self.settlement_cache = {}

    def check_pending_settlements(self) -> List[Dict[str, Any]]:
        """Check status of pending settlements across all banks."""
        pending_settlements = []

        for bank_name, client in self.bank_clients.items():
            if client.is_enabled():
                try:
                    # Get recent transactions and check settlement status
                    transactions = client.get_transaction_history(days=1)
                    if transactions:
                        for tx in transactions:
                            if tx.get("status") in ["pending", "processing"]:
                                settlement_info = {
                                    "bank": bank_name,
                                    "transaction_id": tx.get("id"),
                                    "amount": tx.get("amount"),
                                    "status": tx.get("status"),
                                    "initiated_at": tx.get("created_at")
                                }
                                pending_settlements.append(settlement_info)
                except Exception as e:
                    logger.warning(f"Failed to check settlements for {bank_name}: {e}")

        return pending_settlements

    def get_total_available_balance(self) -> float:
        """Get total available balance across all enabled bank accounts."""
        total_balance = 0.0

        for bank_name, client in self.bank_clients.items():
            if client.is_enabled():
                try:
                    balance = client.get_account_balance()
                    if balance is not None:
                        total_balance += balance
                        logger.debug(f"{bank_name} balance: {balance}")
                except Exception as e:
                    logger.warning(f"Failed to get balance for {bank_name}: {e}")

        return total_balance

    def check_margin_health(self) -> Dict[str, Any]:
        """Check margin health across all margin accounts."""
        margin_health = {
            "total_margin_limit": 0.0,
            "total_margin_used": 0.0,
            "total_margin_available": 0.0,
            "margin_call_alerts": [],
            "accounts": []
        }

        for bank_name, client in self.bank_clients.items():
            if client.is_enabled():
                try:
                    margin_info = client.get_margin_info()
                    if margin_info:
                        margin_health["total_margin_limit"] += margin_info.get("margin_limit", 0)
                        margin_health["total_margin_used"] += margin_info.get("margin_used", 0)
                        margin_health["total_margin_available"] += margin_info.get("margin_available", 0)

                        if margin_info.get("margin_call", False):
                            margin_health["margin_call_alerts"].append({
                                "bank": bank_name,
                                "account": client.config["account_number"],
                                "severity": "CRITICAL"
                            })

                        margin_health["accounts"].append({
                            "bank": bank_name,
                            "margin_info": margin_info
                        })

                except Exception as e:
                    logger.warning(f"Failed to get margin info for {bank_name}: {e}")

        # Calculate overall utilization
        if margin_health["total_margin_limit"] > 0:
            utilization = margin_health["total_margin_used"] / margin_health["total_margin_limit"]
            margin_health["overall_utilization"] = utilization

            # Check against warning/critical thresholds
            if utilization >= BANKING_CONFIG.margin_critical_threshold:
                margin_health["overall_status"] = "CRITICAL"
            elif utilization >= BANKING_CONFIG.margin_warning_threshold:
                margin_health["overall_status"] = "WARNING"
            else:
                margin_health["overall_status"] = "HEALTHY"

        return margin_health


class CapitalManager:
    """Capital allocation and management across bank accounts."""

    def __init__(self):
        self.settlement_monitor = SettlementMonitor()

    def get_capital_overview(self) -> Dict[str, Any]:
        """Get comprehensive capital overview."""
        available_balance = self.settlement_monitor.get_total_available_balance()
        margin_health = self.settlement_monitor.check_margin_health()
        pending_settlements = self.settlement_monitor.check_pending_settlements()

        return {
            "available_balance": available_balance,
            "margin_health": margin_health,
            "pending_settlements": pending_settlements,
            "total_pending_amount": sum(s.get("amount", 0) for s in pending_settlements),
            "timestamp": datetime.now().isoformat()
        }

    def check_capital_adequacy(self, required_amount: float) -> Dict[str, Any]:
        """Check if sufficient capital is available for a transaction."""
        overview = self.get_capital_overview()

        available_for_trading = overview["available_balance"]
        # Reserve some capital for margin requirements
        reserved_for_margin = overview["margin_health"].get("total_margin_available", 0) * 0.1

        effective_available = available_for_trading - reserved_for_margin

        return {
            "required_amount": required_amount,
            "effective_available": effective_available,
            "sufficient": effective_available >= required_amount,
            "shortfall": max(0, required_amount - effective_available),
            "margin_reserved": reserved_for_margin
        }


# Global instances
settlement_monitor = SettlementMonitor()
capital_manager = CapitalManager()


def get_capital_overview() -> Dict[str, Any]:
    """Get capital overview across all accounts."""
    return capital_manager.get_capital_overview()


def check_capital_adequacy(required_amount: float) -> Dict[str, Any]:
    """Check if sufficient capital is available."""
    return capital_manager.check_capital_adequacy(required_amount)


def get_total_balance() -> float:
    """Get total available balance across all accounts."""
    return settlement_monitor.get_total_available_balance()


def check_pending_settlements() -> List[Dict[str, Any]]:
    """Get list of pending settlements."""
    return settlement_monitor.check_pending_settlements()


def check_margin_health() -> Dict[str, Any]:
    """Get margin health status."""
    return settlement_monitor.check_margin_health()