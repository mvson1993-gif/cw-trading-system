from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config.settings import BROKER_CONFIG, HEDGE_POLICY
from ..data.market_data import MarketDataService
from ..data.position_store import load_portfolio
from ..data.positions import Portfolio
from ..utils.logging import get_logger
from .market_making_engine import TradingMode, market_making_engine
from .pricing_engine import price_cw
from .risk_engine import calculate_portfolio_risk

logger = get_logger(__name__)


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class TradingTask:
    """Configuration for one live or simulated CW auto-trading workflow."""

    ticker: str
    underlying: str
    strike: float
    expiry: str
    market_making_enabled: bool = True
    auto_hedging_enabled: bool = True
    interval_seconds: int = 30
    iv_premium: float = 0.10
    spread_pct: float = 0.04
    quote_quantity: int = 100_000
    inventory: int = 0
    trading_mode: str = TradingMode.AUTO.value
    delta_band: float = HEDGE_POLICY.delta_band
    hedge_ratio: float = HEDGE_POLICY.hedge_ratio
    min_trade_size: int = HEDGE_POLICY.min_trade_size
    delta_override: Optional[float] = None
    notes: str = ""
    created_at: str = field(default_factory=_utc_timestamp)


class AutoTradingWorker:
    """Background worker for periodic quote generation and hedge execution.

    This is designed to be usable today in simulation mode and later switched to
    live OCBS routing by providing the real OCBS API implementation.
    """

    def __init__(self, market_data_service: Optional[MarketDataService] = None):
        self.market_data_service = market_data_service or MarketDataService()
        self.scheduler = BackgroundScheduler()
        self.tasks: Dict[str, TradingTask] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}
        self.is_running = False

    def _task_key(self, ticker: str, underlying: str = "") -> str:
        return f"{ticker}::{underlying}".upper()

    def _ensure_scheduler(self) -> None:
        if not self.is_running and getattr(self.scheduler, "state", 0) != 0:
            self.scheduler = BackgroundScheduler()

    def _schedule_task(self, task: TradingTask) -> None:
        job_id = self._task_key(task.ticker, task.underlying)
        self.scheduler.add_job(
            func=self.run_cycle,
            trigger=IntervalTrigger(seconds=max(int(task.interval_seconds), 5)),
            id=job_id,
            name=f"Auto trade {task.ticker}",
            args=[task.ticker, task.underlying],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def start(self) -> Dict[str, Any]:
        """Start the background worker and schedule all registered strategies."""
        if self.is_running:
            return {
                "started": False,
                "status": "already-running",
                "registered_strategies": len(self.tasks),
            }

        self._ensure_scheduler()
        for task in self.tasks.values():
            self._schedule_task(task)

        self.scheduler.start()
        self.is_running = True
        logger.info("Auto trading worker started with %s strategies", len(self.tasks))
        return {
            "started": True,
            "status": "running",
            "registered_strategies": len(self.tasks),
        }

    def stop(self) -> Dict[str, Any]:
        """Stop the worker and all scheduled jobs."""
        if not self.is_running:
            return {
                "stopped": False,
                "status": "already-stopped",
                "registered_strategies": len(self.tasks),
            }

        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("Auto trading worker stopped")
        return {
            "stopped": True,
            "status": "stopped",
            "registered_strategies": len(self.tasks),
        }

    def register_strategy(self, task: TradingTask) -> Dict[str, Any]:
        """Register or update one strategy configuration."""
        key = self._task_key(task.ticker, task.underlying)
        self.tasks[key] = task
        if self.is_running:
            self._schedule_task(task)

        logger.info("Registered auto-trading strategy for %s", key)
        return {
            "registered": True,
            "worker_running": self.is_running,
            "task": asdict(task),
        }

    def unregister_strategy(self, ticker: str, underlying: str = "") -> Dict[str, Any]:
        """Remove one strategy from the worker."""
        key = self._task_key(ticker, underlying)
        removed = self.tasks.pop(key, None) is not None

        try:
            self.scheduler.remove_job(key)
        except Exception:
            pass

        self.last_results.pop(key, None)
        return {
            "removed": removed,
            "key": key,
        }

    def get_status(self, ticker: Optional[str] = None, underlying: str = "") -> Dict[str, Any]:
        """Return overall worker status or one strategy snapshot."""
        if ticker:
            key = self._task_key(ticker, underlying)
            task = self.tasks.get(key)
            return {
                "worker_running": self.is_running,
                "task": asdict(task) if task else None,
                "last_result": self.last_results.get(key),
            }

        return {
            "worker_running": self.is_running,
            "broker_enabled": BROKER_CONFIG.ocbs_enabled,
            "mode": "live" if BROKER_CONFIG.ocbs_enabled else "simulation-ready",
            "registered_strategies": [asdict(task) for task in self.tasks.values()],
            "strategy_count": len(self.tasks),
            "last_updated": _utc_timestamp(),
        }

    def run_cycle(self, ticker: str, underlying: str = "") -> Dict[str, Any]:
        """Run one full market-making and hedging cycle for a registered strategy."""
        key = self._task_key(ticker, underlying)
        task = self.tasks.get(key)
        if not task:
            raise KeyError(f"No trading task registered for {ticker} / {underlying}")

        result: Dict[str, Any] = {
            "success": True,
            "ticker": task.ticker,
            "underlying": task.underlying,
            "timestamp": _utc_timestamp(),
            "broker_mode": "live" if BROKER_CONFIG.ocbs_enabled else "simulation-ready",
            "quote_result": None,
            "hedge_result": None,
        }

        try:
            if task.market_making_enabled:
                pricing = price_cw(self.market_data_service, task.underlying, task.strike, task.expiry)
                quote = market_making_engine.build_two_sided_quote(
                    ticker=task.ticker,
                    underlying=task.underlying,
                    fair_value=pricing["fair_value"],
                    iv_premium=task.iv_premium,
                    spread_pct=task.spread_pct,
                    quantity=task.quote_quantity,
                    inventory=task.inventory,
                    mode=task.trading_mode,
                )
                quote_result = market_making_engine.submit_two_sided_quote(quote, send_orders=True)
                result["pricing"] = pricing
                result["quote_result"] = quote_result

            if task.auto_hedging_enabled:
                net_delta = task.delta_override
                if net_delta is None:
                    net_delta = self._get_underlying_delta(task.underlying)

                decision = market_making_engine.evaluate_hedge_need(
                    underlying=task.underlying,
                    net_delta=net_delta,
                    delta_band=task.delta_band,
                    hedge_ratio=task.hedge_ratio,
                    min_trade_size=task.min_trade_size,
                )
                hedge_result = market_making_engine.execute_hedge_decision(
                    ticker=task.ticker,
                    decision=decision,
                    auto_execute=True,
                )
                result["net_delta"] = net_delta
                result["hedge_result"] = hedge_result

        except Exception as exc:
            logger.exception("Auto trading cycle failed for %s: %s", key, exc)
            result["success"] = False
            result["error"] = str(exc)

        self.last_results[key] = result
        return result

    def run_all_cycles(self) -> Dict[str, Any]:
        """Trigger all registered strategies once immediately."""
        batch_results = {}
        for task in list(self.tasks.values()):
            batch_results[self._task_key(task.ticker, task.underlying)] = self.run_cycle(task.ticker, task.underlying)

        return {
            "success": True,
            "strategy_count": len(batch_results),
            "results": batch_results,
        }

    def _get_underlying_delta(self, underlying: str) -> float:
        """Get current delta exposure for one underlying from the live portfolio."""
        cw_positions, hedge_positions = load_portfolio()
        portfolio = Portfolio(cw_positions, hedge_positions)
        risk = calculate_portfolio_risk(portfolio, self.market_data_service)

        if underlying in risk.get("by_underlying", {}):
            return float(risk["by_underlying"][underlying]["delta"])
        return float(risk["total"]["delta"])


auto_trading_worker = AutoTradingWorker()
