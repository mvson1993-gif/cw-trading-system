# data/cw_data.py

"""
Covered Warrant Data Framework

This module provides a framework for integrating with Covered Warrant data APIs
from various issuers and exchanges. The framework is designed to be extensible
and will be populated with actual API implementations once official APIs are available.

Current Status: Framework only - ready for future API integration
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..config.settings import CW_DATA_CONFIG
from ..utils.logging import get_logger
from ..errors import DataError

logger = get_logger(__name__)


class CWDataError(DataError):
    """Covered Warrant data API error."""
    pass


class CWDataProvider:
    """Base class for CW data providers."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.session = requests.Session()
        self._auth_token = None
        self._token_expiry = None

    def is_enabled(self) -> bool:
        """Check if this provider is enabled."""
        return self.config.get("enabled", False)

    def authenticate(self) -> None:
        """Authenticate with the API. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement authenticate()")

    def get_cw_terms(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get CW terms (strike, expiry, conversion ratio, etc.)."""
        raise NotImplementedError("Subclasses must implement get_cw_terms()")

    def get_cw_price(self, cw_ticker: str) -> Optional[float]:
        """Get current CW price."""
        raise NotImplementedError("Subclasses must implement get_cw_price()")

    def get_cw_volume(self, cw_ticker: str) -> Optional[int]:
        """Get CW trading volume."""
        raise NotImplementedError("Subclasses must implement get_cw_volume()")

    def get_exercise_data(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get exercise/settlement data."""
        raise NotImplementedError("Subclasses must implement get_exercise_data()")


class OCBSIssuerAPI(CWDataProvider):
    """OCBS Covered Warrant API client."""

    def __init__(self):
        config = CW_DATA_CONFIG.issuer_apis["ocbs"]
        super().__init__("OCBS", config)

    def authenticate(self) -> None:
        """Authenticate with OCBS CW API."""
        if not self.is_enabled():
            return

        try:
            auth_url = f"{self.config['base_url']}/auth/login"
            auth_data = {
                "api_key": self.config["api_key"],
                "api_secret": self.config["api_secret"]
            }

            response = self.session.post(auth_url, json=auth_data, timeout=30)
            response.raise_for_status()

            data = response.json()
            self._auth_token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self._auth_token}"})

            logger.info("OCBS CW API authentication successful")

        except Exception as e:
            logger.error(f"OCBS CW API authentication failed: {e}")
            raise CWDataError(f"OCBS authentication failed: {e}")

    def get_cw_terms(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get CW terms from OCBS."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/cw/{cw_ticker}/terms"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "ticker": cw_ticker,
                "underlying": data.get("underlying"),
                "strike": data.get("strike_price"),
                "expiry": data.get("expiry_date"),
                "conversion_ratio": data.get("conversion_ratio"),
                "issuer": "OCBS",
                "type": data.get("type"),  # Call/Put
                "issue_date": data.get("issue_date"),
                "total_issued": data.get("total_issued")
            }

        except Exception as e:
            logger.warning(f"Failed to get CW terms from OCBS for {cw_ticker}: {e}")
            return None

    def get_cw_price(self, cw_ticker: str) -> Optional[float]:
        """Get CW price from OCBS."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/cw/{cw_ticker}/price"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get("last_price")

        except Exception as e:
            logger.warning(f"Failed to get CW price from OCBS for {cw_ticker}: {e}")
            return None

    def get_cw_volume(self, cw_ticker: str) -> Optional[int]:
        """Get CW volume from OCBS."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/cw/{cw_ticker}/volume"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get("volume")

        except Exception as e:
            logger.warning(f"Failed to get CW volume from OCBS for {cw_ticker}: {e}")
            return None

    def get_exercise_data(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get exercise data from OCBS."""
        if not self.is_enabled():
            return None

        try:
            self.authenticate()
            url = f"{self.config['base_url']}/cw/{cw_ticker}/exercise"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "exercised_today": data.get("exercised_today", 0),
                "total_exercised": data.get("total_exercised", 0),
                "exercise_price": data.get("exercise_price"),
                "exercise_date": data.get("exercise_date")
            }

        except Exception as e:
            logger.warning(f"Failed to get exercise data from OCBS for {cw_ticker}: {e}")
            return None


class VietcombankIssuerAPI(CWDataProvider):
    """Vietcombank Covered Warrant API client."""

    def __init__(self):
        config = CW_DATA_CONFIG.issuer_apis["vietcombank"]
        super().__init__("Vietcombank", config)

    def authenticate(self) -> None:
        """Authenticate with Vietcombank CW API."""
        if not self.is_enabled():
            return

        try:
            # Vietcombank uses OAuth2
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
            self.session.headers.update({"Authorization": f"Bearer {self._auth_token}"})

            logger.info("Vietcombank CW API authentication successful")

        except Exception as e:
            logger.error(f"Vietcombank CW API authentication failed: {e}")
            raise CWDataError(f"Vietcombank authentication failed: {e}")

    def get_cw_terms(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get CW terms from Vietcombank."""
        # TODO: Implement when API is available
        logger.info(f"Vietcombank CW API: get_cw_terms for {cw_ticker} - Framework ready")
        return None

    def get_cw_price(self, cw_ticker: str) -> Optional[float]:
        """Get CW price from Vietcombank."""
        # TODO: Implement when API is available
        logger.info(f"Vietcombank CW API: get_cw_price for {cw_ticker} - Framework ready")
        return None

    def get_cw_volume(self, cw_ticker: str) -> Optional[int]:
        """Get CW volume from Vietcombank."""
        # TODO: Implement when API is available
        logger.info(f"Vietcombank CW API: get_cw_volume for {cw_ticker} - Framework ready")
        return None

    def get_exercise_data(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get exercise data from Vietcombank."""
        # TODO: Implement when API is available
        logger.info(f"Vietcombank CW API: get_exercise_data for {cw_ticker} - Framework ready")
        return None


class HSBCIssuerAPI(CWDataProvider):
    """HSBC Vietnam Covered Warrant API client."""

    def __init__(self):
        config = CW_DATA_CONFIG.issuer_apis["hsbc"]
        super().__init__("HSBC", config)

    def authenticate(self) -> None:
        """Authenticate with HSBC CW API."""
        if not self.is_enabled():
            return

        try:
            # HSBC uses API key authentication
            self.session.headers.update({
                "X-API-Key": self.config["api_key"],
                "X-API-Secret": self.config["api_secret"]
            })

            logger.info("HSBC CW API authentication configured")

        except Exception as e:
            logger.error(f"HSBC CW API authentication failed: {e}")
            raise CWDataError(f"HSBC authentication failed: {e}")

    def get_cw_terms(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get CW terms from HSBC."""
        # TODO: Implement when API is available
        logger.info(f"HSBC CW API: get_cw_terms for {cw_ticker} - Framework ready")
        return None

    def get_cw_price(self, cw_ticker: str) -> Optional[float]:
        """Get CW price from HSBC."""
        # TODO: Implement when API is available
        logger.info(f"HSBC CW API: get_cw_price for {cw_ticker} - Framework ready")
        return None

    def get_cw_volume(self, cw_ticker: str) -> Optional[int]:
        """Get CW volume from HSBC."""
        # TODO: Implement when API is available
        logger.info(f"HSBC CW API: get_cw_volume for {cw_ticker} - Framework ready")
        return None

    def get_exercise_data(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get exercise data from HSBC."""
        # TODO: Implement when API is available
        logger.info(f"HSBC CW API: get_exercise_data for {cw_ticker} - Framework ready")
        return None


class ExchangeCWDataProvider:
    """Exchange CW data provider for HOSE/HNX."""

    def __init__(self):
        self.hose_url = CW_DATA_CONFIG.hose_cw_url
        self.hnx_url = CW_DATA_CONFIG.hnx_cw_url
        self.session = requests.Session()

    def get_hose_cw_list(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of CWs from HOSE."""
        if not CW_DATA_CONFIG.exchange_cw_enabled:
            return None

        try:
            response = self.session.get(self.hose_url, timeout=15)
            response.raise_for_status()

            data = response.json()
            return data.get("cw_list", [])

        except Exception as e:
            logger.warning(f"Failed to get HOSE CW list: {e}")
            return None

    def get_hnx_cw_list(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of CWs from HNX."""
        if not CW_DATA_CONFIG.exchange_cw_enabled:
            return None

        try:
            response = self.session.get(self.hnx_url, timeout=15)
            response.raise_for_status()

            data = response.json()
            return data.get("cw_list", [])

        except Exception as e:
            logger.warning(f"Failed to get HNX CW list: {e}")
            return None

    def get_all_cw_list(self) -> List[Dict[str, Any]]:
        """Get combined CW list from all exchanges."""
        all_cws = []

        hose_cws = self.get_hose_cw_list()
        if hose_cws:
            all_cws.extend(hose_cws)

        hnx_cws = self.get_hnx_cw_list()
        if hnx_cws:
            all_cws.extend(hnx_cws)

        return all_cws


class CWDataManager:
    """Unified CW data manager with multiple providers."""

    def __init__(self):
        self.issuer_providers = {
            "ocbs": OCBSIssuerAPI(),
            "vietcombank": VietcombankIssuerAPI(),
            "hsbc": HSBCIssuerAPI()
        }
        self.exchange_provider = ExchangeCWDataProvider()
        self._cw_cache = {}  # Cache for CW data

    def get_cw_terms(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get CW terms from available providers."""
        if not CW_DATA_CONFIG.cw_data_enabled:
            logger.debug("CW data APIs disabled")
            return None

        # Check cache first
        if cw_ticker in self._cw_cache:
            cached_data = self._cw_cache[cw_ticker]
            if (datetime.now() - cached_data.get("cached_at", datetime.min)).seconds < 300:  # 5 min cache
                return cached_data.get("terms")

        # Try each issuer provider
        for provider_name, provider in self.issuer_providers.items():
            if provider.is_enabled():
                terms = provider.get_cw_terms(cw_ticker)
                if terms:
                    # Cache the result
                    self._cw_cache[cw_ticker] = {
                        "terms": terms,
                        "cached_at": datetime.now(),
                        "provider": provider_name
                    }
                    logger.info(f"Got CW terms for {cw_ticker} from {provider_name}")
                    return terms

        logger.warning(f"No CW terms found for {cw_ticker} from any provider")
        return None

    def get_cw_price(self, cw_ticker: str) -> Optional[float]:
        """Get CW price from available providers."""
        if not CW_DATA_CONFIG.cw_data_enabled:
            return None

        # Try each issuer provider
        for provider_name, provider in self.issuer_providers.items():
            if provider.is_enabled():
                price = provider.get_cw_price(cw_ticker)
                if price is not None:
                    logger.debug(f"Got CW price for {cw_ticker} from {provider_name}: {price}")
                    return price

        logger.debug(f"No CW price found for {cw_ticker} from any provider")
        return None

    def get_cw_volume(self, cw_ticker: str) -> Optional[int]:
        """Get CW volume from available providers."""
        if not CW_DATA_CONFIG.cw_data_enabled:
            return None

        # Try each issuer provider
        for provider_name, provider in self.issuer_providers.items():
            if provider.is_enabled():
                volume = provider.get_cw_volume(cw_ticker)
                if volume is not None:
                    logger.debug(f"Got CW volume for {cw_ticker} from {provider_name}: {volume}")
                    return volume

        return None

    def get_exercise_data(self, cw_ticker: str) -> Optional[Dict[str, Any]]:
        """Get exercise data from available providers."""
        if not CW_DATA_CONFIG.cw_data_enabled:
            return None

        # Try each issuer provider
        for provider_name, provider in self.issuer_providers.items():
            if provider.is_enabled():
                exercise_data = provider.get_exercise_data(cw_ticker)
                if exercise_data:
                    logger.debug(f"Got exercise data for {cw_ticker} from {provider_name}")
                    return exercise_data

        return None

    def get_all_cw_list(self) -> List[Dict[str, Any]]:
        """Get comprehensive CW list from exchanges."""
        if not CW_DATA_CONFIG.exchange_cw_enabled:
            return []

        return self.exchange_provider.get_all_cw_list()

    def refresh_cache(self) -> None:
        """Refresh CW data cache."""
        self._cw_cache.clear()
        logger.info("CW data cache refreshed")


# Global instance
cw_data_manager = CWDataManager()


def get_cw_terms(cw_ticker: str) -> Optional[Dict[str, Any]]:
    """Get CW terms for a ticker."""
    return cw_data_manager.get_cw_terms(cw_ticker)


def get_cw_price(cw_ticker: str) -> Optional[float]:
    """Get current CW price."""
    return cw_data_manager.get_cw_price(cw_ticker)


def get_cw_volume(cw_ticker: str) -> Optional[int]:
    """Get CW trading volume."""
    return cw_data_manager.get_cw_volume(cw_ticker)


def get_exercise_data(cw_ticker: str) -> Optional[Dict[str, Any]]:
    """Get CW exercise data."""
    return cw_data_manager.get_exercise_data(cw_ticker)


def get_all_cw_list() -> List[Dict[str, Any]]:
    """Get all available CWs."""
    return cw_data_manager.get_all_cw_list()