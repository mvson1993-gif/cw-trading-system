# data/positions.py

from dataclasses import dataclass
from datetime import date
from typing import List, Dict


# =========================
# CW POSITION OBJECT
# =========================

@dataclass
class CWPosition:
    underlying: str
    ticker: str
    cw_qty: int
    conversion_ratio: float
    strike: float
    expiry: str
    issue_price: float
    sigma: float

    def time_to_expiry(self) -> float:
        T = (date.fromisoformat(self.expiry) - date.today()).days / 365
        return max(T, 0.0001)  # avoid zero


# =========================
# HEDGE POSITION OBJECT
# =========================

@dataclass
class HedgePosition:
    underlying: str
    shares: int
    avg_price: float


# =========================
# PORTFOLIO CONTAINER
# =========================

class Portfolio:

    def __init__(self,
                 cw_positions: List[CWPosition],
                 hedge_positions: List[HedgePosition]):

        self.cw_positions = cw_positions
        self.hedge_positions = hedge_positions

        self._validate()

    # -------------------------
    # VALIDATION (CRITICAL)
    # -------------------------

    def _validate(self):

        for pos in self.cw_positions:

            if pos.cw_qty < 0:
                raise ValueError(f"Negative CW quantity: {pos}")

            if pos.strike <= 0:
                raise ValueError(f"Invalid strike: {pos}")

            if pos.conversion_ratio <= 0:
                raise ValueError(f"Invalid conversion ratio: {pos}")

        for hedge in self.hedge_positions:

            if hedge.shares < 0:
                raise ValueError(f"Negative hedge shares: {hedge}")

    # -------------------------
    # GROUPING
    # -------------------------

    def get_underlyings(self) -> List[str]:
        return list(set([p.underlying for p in self.cw_positions]))

    def get_cw_by_underlying(self) -> Dict[str, List[CWPosition]]:
        grouped = {}

        for pos in self.cw_positions:
            grouped.setdefault(pos.underlying, []).append(pos)

        return grouped

    def get_hedge_dict(self) -> Dict[str, HedgePosition]:
        return {h.underlying: h for h in self.hedge_positions}

