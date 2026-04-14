from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Union

from ..brokers.ocbs_client import ocbs_client
from ..config.settings import BROKER_CONFIG, HEDGE_POLICY, RISK_LIMITS
from ..utils.logging import get_logger
from .trade_execution_engine import trade_execution_engine

logger = get_logger(__name__)


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class TradingMode(Enum):
    """Supported trading modes for live controls."""

    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    AUTO = "auto"

    @classmethod
    def from_value(cls, value: Union["TradingMode", str]) -> "TradingMode":
        if isinstance(value, cls):
            return value

        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        for mode in cls:
            if mode.value == normalized:
                return mode
        raise ValueError(f"Unsupported trading mode: {value}")


class StrategyStatus(Enum):
    """Workflow state for market making and hedging."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    BLOCKED = "blocked"


@dataclass
class WorkflowState:
    ticker: str
    underlying: str = ""
    market_making_mode: str = TradingMode.MANUAL.value
    market_making_status: str = StrategyStatus.IDLE.value
    hedge_mode: str = TradingMode.MANUAL.value
    hedge_status: str = StrategyStatus.IDLE.value
    kill_switch: bool = False
    last_quote_time: str | None = None
    last_hedge_time: str | None = None
    last_message: str = "Awaiting trader input"
    updated_at: str = field(default_factory=_utc_timestamp)


class MarketMakingEngine:
    """Desk workflow helper for live CW market making and hedging controls."""

    def __init__(self):
        self.ocbs_client = ocbs_client
        self._workflows: Dict[str, WorkflowState] = {}

    def _state_key(self, ticker: str, underlying: str = "") -> str:
        return f"{ticker}::{underlying or ''}".upper()

    def _get_state(self, ticker: str, underlying: str = "") -> WorkflowState:
        key = self._state_key(ticker, underlying)
        if key not in self._workflows:
            self._workflows[key] = WorkflowState(ticker=ticker, underlying=underlying)
        return self._workflows[key]

    def _update_timestamp(self, state: WorkflowState, message: str) -> None:
        state.last_message = message
        state.updated_at = _utc_timestamp()

    def get_workflow_state(self, ticker: str, underlying: str = "") -> Dict[str, Any]:
        """Return the current state machine snapshot for a live strategy."""
        return asdict(self._get_state(ticker, underlying))

    def set_market_making_mode(
        self,
        ticker: str,
        mode: Union[TradingMode, str],
        enabled: bool,
        underlying: str = "",
    ) -> Dict[str, Any]:
        state = self._get_state(ticker, underlying)
        resolved_mode = TradingMode.from_value(mode)
        state.market_making_mode = resolved_mode.value

        if state.kill_switch and enabled:
            state.market_making_status = StrategyStatus.BLOCKED.value
            self._update_timestamp(state, "Market making blocked by kill switch")
        else:
            state.market_making_status = StrategyStatus.RUNNING.value if enabled else StrategyStatus.STOPPED.value
            action = "started" if enabled else "paused"
            self._update_timestamp(state, f"Market making {action} in {resolved_mode.value} mode")

        snapshot = self.get_workflow_state(ticker, underlying)
        snapshot["status"] = state.market_making_status
        snapshot["mode"] = state.market_making_mode
        return snapshot

    def set_hedging_mode(
        self,
        ticker: str,
        mode: Union[TradingMode, str],
        enabled: bool,
        underlying: str = "",
    ) -> Dict[str, Any]:
        state = self._get_state(ticker, underlying)
        resolved_mode = TradingMode.from_value(mode)
        state.hedge_mode = resolved_mode.value

        if state.kill_switch and enabled:
            state.hedge_status = StrategyStatus.BLOCKED.value
            self._update_timestamp(state, "Auto hedging blocked by kill switch")
        else:
            state.hedge_status = StrategyStatus.RUNNING.value if enabled else StrategyStatus.STOPPED.value
            action = "enabled" if enabled else "paused"
            self._update_timestamp(state, f"Auto hedge {action} in {resolved_mode.value} mode")

        snapshot = self.get_workflow_state(ticker, underlying)
        snapshot["status"] = state.hedge_status
        snapshot["mode"] = state.hedge_mode
        return snapshot

    def set_kill_switch(self, ticker: str, active: bool, underlying: str = "") -> Dict[str, Any]:
        state = self._get_state(ticker, underlying)
        state.kill_switch = active

        if active:
            state.market_making_status = StrategyStatus.BLOCKED.value
            state.hedge_status = StrategyStatus.BLOCKED.value
            self._update_timestamp(state, "Kill switch activated - all live trading blocked")
        else:
            state.market_making_status = StrategyStatus.IDLE.value
            state.hedge_status = StrategyStatus.IDLE.value
            self._update_timestamp(state, "Kill switch released - desk ready")

        snapshot = self.get_workflow_state(ticker, underlying)
        snapshot["status"] = StrategyStatus.BLOCKED.value if active else StrategyStatus.IDLE.value
        return snapshot

    def build_two_sided_quote(
        self,
        ticker: str,
        underlying: str,
        fair_value: float,
        iv_premium: float = 0.10,
        spread_pct: float = 0.04,
        quantity: int = 100_000,
        inventory: int = 0,
        mode: Union[TradingMode, str] = TradingMode.MANUAL,
    ) -> Dict[str, Any]:
        """Build a two-sided CW quote around fair value with IV premium and inventory skew."""
        resolved_mode = TradingMode.from_value(mode)
        base_qty = max(int(quantity), 1)
        adjusted_fair_value = max(float(fair_value) * (1 + float(iv_premium)), 0.01)
        inventory_skew = min(abs(int(inventory)) / base_qty, 0.50)

        # Shift mid-price slightly to encourage inventory normalization.
        shift = adjusted_fair_value * min(inventory_skew * 0.5, 0.02)
        mid_price = adjusted_fair_value - shift if inventory > 0 else adjusted_fair_value + shift if inventory < 0 else adjusted_fair_value

        half_spread = max(mid_price * float(spread_pct) / 2, 0.01)
        bid_price = round(max(mid_price - half_spread, 0.01), 4)
        ask_price = round(mid_price + half_spread, 4)

        bid_quantity = int(base_qty * (1 - inventory_skew)) if inventory < 0 else base_qty
        ask_quantity = int(base_qty * (1 - inventory_skew)) if inventory > 0 else base_qty

        return {
            "ticker": ticker,
            "underlying": underlying,
            "fair_value": round(float(fair_value), 4),
            "theoretical_price": round(adjusted_fair_value, 4),
            "bid_price": bid_price,
            "ask_price": ask_price,
            "bid_quantity": max(bid_quantity, 1),
            "ask_quantity": max(ask_quantity, 1),
            "spread_pct": round(float(spread_pct), 4),
            "iv_premium": round(float(iv_premium), 4),
            "inventory": int(inventory),
            "mode": resolved_mode.value,
            "generated_at": _utc_timestamp(),
        }

    def validate_quote(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Apply basic risk checks before quote submission."""
        checks = []

        if quote["bid_price"] <= 0 or quote["ask_price"] <= 0:
            checks.append("Quote prices must be positive")
        if quote["bid_price"] >= quote["ask_price"]:
            checks.append("Bid must be lower than ask")
        if max(int(quote["bid_quantity"]), int(quote["ask_quantity"])) > RISK_LIMITS.max_position_per_cw:
            checks.append("Quote size exceeds max position per CW")

        return {
            "is_valid": not checks,
            "status": StrategyStatus.RUNNING.value if not checks else StrategyStatus.BLOCKED.value,
            "checks": checks,
        }

    def submit_two_sided_quote(self, quote: Dict[str, Any], send_orders: bool = True) -> Dict[str, Any]:
        """Submit a buy and sell quote to OCBS, or simulate if broker is disabled."""
        state = self._get_state(quote["ticker"], quote.get("underlying", ""))
        validation = self.validate_quote(quote)

        if state.kill_switch:
            validation["is_valid"] = False
            validation["status"] = StrategyStatus.BLOCKED.value
            validation["checks"].append("Kill switch is active")

        if not validation["is_valid"]:
            self._update_timestamp(state, "Quote submission blocked by risk checks")
            return {
                "success": False,
                "status": StrategyStatus.BLOCKED.value,
                "quote": quote,
                "checks": validation["checks"],
            }

        orders = [
            {
                "symbol": quote["ticker"],
                "side": "buy",
                "quantity": int(quote["bid_quantity"]),
                "price": float(quote["bid_price"]),
                "order_type": "limit",
                "time_in_force": "day",
            },
            {
                "symbol": quote["ticker"],
                "side": "sell",
                "quantity": int(quote["ask_quantity"]),
                "price": float(quote["ask_price"]),
                "order_type": "limit",
                "time_in_force": "day",
            },
        ]

        responses = []
        for order in orders:
            if send_orders and BROKER_CONFIG.ocbs_enabled:
                response = self.ocbs_client.place_order(order)
            else:
                response = {
                    "order_id": f"SIM-{quote['ticker']}-{order['side'].upper()}",
                    "status": "simulated" if not BROKER_CONFIG.ocbs_enabled else "prepared",
                    "submitted_price": order["price"],
                    "submitted_quantity": order["quantity"],
                }
            responses.append({**order, **response})

        state.market_making_status = StrategyStatus.RUNNING.value
        state.last_quote_time = _utc_timestamp()
        self._update_timestamp(state, "Two-sided market making quote submitted")

        return {
            "success": True,
            "status": StrategyStatus.RUNNING.value,
            "quote": quote,
            "orders": responses,
            "broker_enabled": BROKER_CONFIG.ocbs_enabled,
        }

    def evaluate_hedge_need(
        self,
        underlying: str,
        net_delta: float,
        delta_band: float | None = None,
        hedge_ratio: float | None = None,
        min_trade_size: int | None = None,
    ) -> Dict[str, Any]:
        """Generate a manual/auto hedge recommendation from delta exposure."""
        delta_band = float(HEDGE_POLICY.delta_band if delta_band is None else delta_band)
        hedge_ratio = float(HEDGE_POLICY.hedge_ratio if hedge_ratio is None else hedge_ratio)
        min_trade_size = int(HEDGE_POLICY.min_trade_size if min_trade_size is None else min_trade_size)

        if abs(net_delta) <= delta_band:
            return {
                "requires_hedge": False,
                "status": StrategyStatus.IDLE.value,
                "underlying": underlying,
                "side": "hold",
                "quantity": 0,
                "reason": f"Net delta {net_delta:,.0f} is within the {delta_band:,.0f} band",
            }

        side = "sell" if net_delta > 0 else "buy"
        quantity = max(int(round(abs(net_delta) * hedge_ratio)), min_trade_size)

        return {
            "requires_hedge": True,
            "status": StrategyStatus.RUNNING.value,
            "underlying": underlying,
            "side": side,
            "quantity": quantity,
            "reason": f"Net delta {net_delta:,.0f} breached the {delta_band:,.0f} band",
        }

    def execute_hedge_decision(
        self,
        ticker: str,
        decision: Dict[str, Any],
        auto_execute: bool = False,
    ) -> Dict[str, Any]:
        """Execute or stage a hedge action depending on desk mode."""
        state = self._get_state(ticker, decision.get("underlying", ""))

        if state.kill_switch:
            self._update_timestamp(state, "Hedge blocked by kill switch")
            return {
                "success": False,
                "status": StrategyStatus.BLOCKED.value,
                "decision": decision,
                "message": "Kill switch is active",
            }

        if not decision.get("requires_hedge"):
            state.hedge_status = StrategyStatus.IDLE.value
            self._update_timestamp(state, "No hedge action required")
            return {
                "success": True,
                "status": StrategyStatus.IDLE.value,
                "decision": decision,
                "message": decision.get("reason", "No hedge required"),
            }

        state.last_hedge_time = _utc_timestamp()

        if auto_execute and BROKER_CONFIG.ocbs_enabled:
            result = trade_execution_engine.execute_hedge_trade(
                {
                    "underlying": decision["underlying"],
                    "side": decision["side"],
                    "quantity": decision["quantity"],
                    "reason": decision["reason"],
                }
            )
            state.hedge_status = StrategyStatus.RUNNING.value
            self._update_timestamp(state, "Auto hedge order submitted to OCBS")
            return {
                "success": True,
                "status": StrategyStatus.RUNNING.value,
                "decision": decision,
                "execution": result,
                "broker_enabled": True,
            }

        state.hedge_status = StrategyStatus.RUNNING.value if auto_execute else StrategyStatus.IDLE.value
        mode_label = "auto-staged" if auto_execute else "manual-review"
        self._update_timestamp(state, f"Hedge decision prepared in {mode_label} mode")
        return {
            "success": True,
            "status": state.hedge_status,
            "decision": decision,
            "broker_enabled": BROKER_CONFIG.ocbs_enabled,
            "message": "Hedge order prepared" if auto_execute else "Review and submit hedge manually",
        }


market_making_engine = MarketMakingEngine()
