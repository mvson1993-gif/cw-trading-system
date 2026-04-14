"""Centralized application exception types."""

class AppError(Exception):
    """Base class for all application errors."""


class ConfigurationError(AppError):
    """Configuration is invalid or missing."""


class DataError(AppError):
    """Data processing or persistence issue."""


class BrokerError(AppError):
    """Broker integration issue."""


class ReconciliationError(AppError):
    """Reconciliation engine issue."""


class TradeExecutionError(AppError):
    """Trade execution issue."""
