# config/settings.py

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# =========================
# ENVIRONMENT VARIABLES
# =========================

ENV = os.getenv("ENV", "development")  # development, staging, production
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# =========================
# DATABASE CONFIGURATION
# =========================

@dataclass
class DatabaseConfig:
    url: str
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

DATABASE = DatabaseConfig(
    url=os.getenv("DATABASE_URL", "sqlite:///./cw_trading.db"),
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
)

# =========================
# LOGGING CONFIGURATION
# =========================

@dataclass
class LoggingConfig:
    level: str
    log_dir: str

LOGGING = LoggingConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "logs"),
)

# =========================
# MARKET ASSUMPTIONS
# =========================

RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.05"))
TRADING_DAYS = int(os.getenv("TRADING_DAYS", "252"))
DEFAULT_VOL = float(os.getenv("DEFAULT_VOL", "0.30"))

# =========================
# RISK LIMITS (DESK LEVEL)
# =========================

@dataclass
class RiskLimits:
    max_delta: float = float(os.getenv("MAX_DELTA", "2000000"))
    max_gamma: float = float(os.getenv("MAX_GAMMA", "50000"))
    max_vega: float = float(os.getenv("MAX_VEGA", "200000"))
    max_position_per_cw: int = int(os.getenv("MAX_POSITION_PER_CW", "5000000"))
    max_loss_daily: float = float(os.getenv("MAX_LOSS_DAILY", "-5000000000"))


RISK_LIMITS = RiskLimits()

# =========================
# ALERTING CONFIGURATION
# =========================

@dataclass
class AlertConfig:
    email_enabled: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_to: str = os.getenv("EMAIL_TO", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    sms_enabled: bool = os.getenv("SMS_ENABLED", "false").lower() == "true"
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from_number: str = os.getenv("TWILIO_FROM_NUMBER", "")
    sms_to_number: str = os.getenv("SMS_TO_NUMBER", "")


ALERT_CONFIG = AlertConfig()

# =========================
# BROKER API CONFIGURATION
# =========================

@dataclass
class BrokerConfig:
    ocbs_enabled: bool = os.getenv("OCBS_ENABLED", "false").lower() == "true"
    ocbs_base_url: str = os.getenv("OCBS_BASE_URL", "https://api.ocbs.com")
    ocbs_api_key: str = os.getenv("OCBS_API_KEY", "")
    ocbs_api_secret: str = os.getenv("OCBS_API_SECRET", "")
    ocbs_timeout: int = int(os.getenv("OCBS_TIMEOUT", "30"))
    ocbs_sandbox_mode: bool = os.getenv("OCBS_SANDBOX_MODE", "false").lower() == "true"
    ocbs_sandbox_account: str = os.getenv("OCBS_SANDBOX_ACCOUNT", "SANDBOX-001")
    reconciliation_enabled: bool = os.getenv("RECONCILIATION_ENABLED", "false").lower() == "true"
    reconciliation_interval_hours: int = int(os.getenv("RECONCILIATION_INTERVAL_HOURS", "24"))


BROKER_CONFIG = BrokerConfig()

# =========================
# VN MARKET DATA API CONFIGURATION
# =========================

@dataclass
class VNMarketDataConfig:
    # VNDirect API
    vndirect_enabled: bool = os.getenv("VNDIRECT_ENABLED", "false").lower() == "true"
    vndirect_base_url: str = os.getenv("VNDIRECT_BASE_URL", "https://api.vndirect.com.vn")
    vndirect_api_key: str = os.getenv("VNDIRECT_API_KEY", "")
    vndirect_api_secret: str = os.getenv("VNDIRECT_API_SECRET", "")

    # SSI API
    ssi_enabled: bool = os.getenv("SSI_ENABLED", "false").lower() == "true"
    ssi_base_url: str = os.getenv("SSI_BASE_URL", "https://api.ssi.com.vn")
    ssi_api_key: str = os.getenv("SSI_API_KEY", "")
    ssi_api_secret: str = os.getenv("SSI_API_SECRET", "")

    # FTS API
    fts_enabled: bool = os.getenv("FTS_ENABLED", "false").lower() == "true"
    fts_base_url: str = os.getenv("FTS_BASE_URL", "https://api.fts.com.vn")
    fts_api_key: str = os.getenv("FTS_API_KEY", "")
    fts_api_secret: str = os.getenv("FTS_API_SECRET", "")

    # Real-time streaming
    websocket_enabled: bool = os.getenv("WEBSOCKET_ENABLED", "false").lower() == "true"
    websocket_url: str = os.getenv("WEBSOCKET_URL", "wss://websocket.vndirect.com.vn")
    websocket_timeout: int = int(os.getenv("WEBSOCKET_TIMEOUT", "30"))

    # Fallback priority: vndirect > ssi > fts > yfinance > mock
    provider_priority: List[str] = field(default_factory=lambda: ["vndirect", "ssi", "fts", "yfinance", "mock"])


VN_MARKET_CONFIG = VNMarketDataConfig()

# =========================
# COVERED WARRANT DATA API CONFIGURATION
# =========================

@dataclass
class CWDataConfig:
    # Framework for future CW data APIs
    cw_data_enabled: bool = os.getenv("CW_DATA_ENABLED", "false").lower() == "true"

    # Issuer APIs (placeholders for future implementation)
    issuer_apis: Dict[str, Dict] = field(default_factory=lambda: {
        "ocbs": {
            "enabled": os.getenv("CW_OCBS_ENABLED", "false").lower() == "true",
            "base_url": os.getenv("CW_OCBS_BASE_URL", "https://cw-api.ocbs.com"),
            "api_key": os.getenv("CW_OCBS_API_KEY", ""),
            "api_secret": os.getenv("CW_OCBS_API_SECRET", "")
        },
        "vietcombank": {
            "enabled": os.getenv("CW_VIETCOMBANK_ENABLED", "false").lower() == "true",
            "base_url": os.getenv("CW_VIETCOMBANK_BASE_URL", "https://cw-api.vietcombank.com.vn"),
            "api_key": os.getenv("CW_VIETCOMBANK_API_KEY", ""),
            "api_secret": os.getenv("CW_VIETCOMBANK_API_SECRET", "")
        },
        "hsbc": {
            "enabled": os.getenv("CW_HSBC_ENABLED", "false").lower() == "true",
            "base_url": os.getenv("CW_HSBC_BASE_URL", "https://cw-api.hsbc.com.vn"),
            "api_key": os.getenv("CW_HSBC_API_KEY", ""),
            "api_secret": os.getenv("CW_HSBC_API_SECRET", "")
        }
    })

    # Exchange CW data
    exchange_cw_enabled: bool = os.getenv("EXCHANGE_CW_ENABLED", "false").lower() == "true"
    hose_cw_url: str = os.getenv("HOSE_CW_URL", "https://api.hose.com.vn/cw")
    hnx_cw_url: str = os.getenv("HNX_CW_URL", "https://api.hnx.com.vn/cw")


CW_DATA_CONFIG = CWDataConfig()

# =========================
# BANKING & SETTLEMENT API CONFIGURATION
# =========================

@dataclass
class BankingConfig:
    banking_enabled: bool = os.getenv("BANKING_ENABLED", "false").lower() == "true"

    # Bank APIs
    banks: Dict[str, Dict] = field(default_factory=lambda: {
        "vietcombank": {
            "enabled": os.getenv("VCB_ENABLED", "false").lower() == "true",
            "base_url": os.getenv("VCB_BASE_URL", "https://api.vietcombank.com.vn"),
            "api_key": os.getenv("VCB_API_KEY", ""),
            "api_secret": os.getenv("VCB_API_SECRET", ""),
            "account_number": os.getenv("VCB_ACCOUNT_NUMBER", "")
        },
        "techcombank": {
            "enabled": os.getenv("TCB_ENABLED", "false").lower() == "true",
            "base_url": os.getenv("TCB_BASE_URL", "https://api.techcombank.com.vn"),
            "api_key": os.getenv("TCB_API_KEY", ""),
            "api_secret": os.getenv("TCB_API_SECRET", ""),
            "account_number": os.getenv("TCB_ACCOUNT_NUMBER", "")
        },
        "vietinbank": {
            "enabled": os.getenv("VTB_ENABLED", "false").lower() == "true",
            "base_url": os.getenv("VTB_BASE_URL", "https://api.vietinbank.vn"),
            "api_key": os.getenv("VTB_API_KEY", ""),
            "api_secret": os.getenv("VTB_API_SECRET", ""),
            "account_number": os.getenv("VTB_ACCOUNT_NUMBER", "")
        }
    })

    # Settlement configuration
    settlement_enabled: bool = os.getenv("SETTLEMENT_ENABLED", "false").lower() == "true"
    settlement_check_interval: int = int(os.getenv("SETTLEMENT_CHECK_INTERVAL", "3600"))  # seconds

    # Margin monitoring
    margin_monitoring_enabled: bool = os.getenv("MARGIN_MONITORING_ENABLED", "false").lower() == "true"
    margin_warning_threshold: float = float(os.getenv("MARGIN_WARNING_THRESHOLD", "0.8"))  # 80%
    margin_critical_threshold: float = float(os.getenv("MARGIN_CRITICAL_THRESHOLD", "0.95"))  # 95%


BANKING_CONFIG = BankingConfig()

# =========================
# HEDGING POLICY
# =========================

@dataclass
class HedgePolicy:
    delta_band: float = float(os.getenv("DELTA_BAND", "100000"))
    hedge_ratio: float = float(os.getenv("HEDGE_RATIO", "1.0"))
    min_trade_size: int = int(os.getenv("MIN_TRADE_SIZE", "10000"))


HEDGE_POLICY = HedgePolicy()

# =========================
# STRESS SCENARIOS
# =========================

STRESS_SHOCKS = [
    -0.10,
    -0.05,
    0.05,
    0.10
]

# =========================
# PRICING SETTINGS
# =========================

@dataclass
class PricingConfig:
    use_intrinsic_proxy: bool = True
    vol_shift: float = 0.0


PRICING_CONFIG = PricingConfig()

# =========================
# STORAGE PATHS
# =========================

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
LOGS_DIR = BASE_DIR / LOGGING.log_dir

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
