# data/position_store.py

from datetime import date
from .positions import CWPosition, HedgePosition
from .repositories import PositionRepository

# Initialize repository instance
_position_repo = PositionRepository(file_path="data/positions.json")


# =========================
# LOAD
# =========================

def load_portfolio():
    """Load portfolio from repository.
    
    Returns:
        Tuple of (cw_positions, hedge_positions)
    """
    return _position_repo.load_portfolio()


# =========================
# SAVE
# =========================

def save_portfolio(cw_positions, hedge_positions):
    """Save portfolio to repository.
    
    Args:
        cw_positions: List of CW positions
        hedge_positions: List of hedge positions
    """
    _position_repo.save_portfolio(cw_positions, hedge_positions)


# =========================
# ADD CW
# =========================

def add_cw(new_pos, cw_positions, hedge_positions):
    """Add a new CW position.
    
    Args:
        new_pos: CW position to add
        cw_positions: Current CW positions list
        hedge_positions: Current hedge positions list
    """
    _position_repo.add_cw_position(new_pos, cw_positions, hedge_positions)


# =========================
# REMOVE CW
# =========================

def remove_cw(index, cw_positions, hedge_positions):
    """Remove CW position by index.
    
    Args:
        index: Index of position to remove
        cw_positions: Current CW positions list
        hedge_positions: Current hedge positions list
    """
    _position_repo.remove_cw_position(index, cw_positions, hedge_positions)


# =========================
# REMOVE EXPIRED
# =========================

def remove_expired(cw_positions, hedge_positions):
    """Remove expired CW positions.
    
    Args:
        cw_positions: Current CW positions list
        hedge_positions: Current hedge positions list
        
    Returns:
        Updated list of non-expired CW positions
    """
    return _position_repo.remove_expired_positions(cw_positions, hedge_positions)
