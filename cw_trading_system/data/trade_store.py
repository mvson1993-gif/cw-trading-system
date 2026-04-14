# data/trade_store.py

from datetime import datetime
from .repositories import TradeRepository

# Initialize repository instance
_trade_repo = TradeRepository(file_path="data/trades.json")


def load_trades():
    """Load all trades from repository.
    
    Returns:
        List of trade records
    """
    return _trade_repo.load_all_trades()


def save_trades(trades):
    """Save trades list to repository (replaces entire store).
    
    Args:
        trades: List of trade dictionaries
    """
    _trade_repo._write_data(trades)


def record_trade(underlying, action, size, price):
    """Record a single trade execution.
    
    Args:
        underlying: Underlying asset symbol
        action: Trade action (BUY/SELL/HEDGE)
        size: Quantity traded
        price: Execution price
    """
    _trade_repo.record_trade(underlying, action, size, price)
