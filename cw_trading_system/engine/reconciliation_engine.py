# engine/reconciliation_engine.py

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, TypedDict
from sqlalchemy.exc import SQLAlchemyError
from ..brokers.ocbs_client import ocbs_client, OCBSAPIError


class InternalTrade(TypedDict, total=False):
    trade_id: str
    underlying: str
    quantity: float
    execution_time: datetime
    price: float
    action: str


class BrokerTrade(TypedDict, total=False):
    trade_id: str
    symbol: str
    quantity: float
    execution_time: datetime
    price: float
from ..data.position_store import load_portfolio
from ..data.market_data import MarketDataService
from ..database.models import AuditEvent, AuditEventType
from ..database import get_session
# backwards compatibility for tests and helpers
from ..database import get_session as get_db_session
from ..utils.logging import get_logger
from ..utils.alerting import alert_manager
from ..config.settings import BROKER_CONFIG

logger = get_logger(__name__)


class ReconciliationError(Exception):
    """Reconciliation error."""
    pass


class ReconciliationEngine:
    """Engine for reconciling internal positions with broker positions."""

    def __init__(self):
        self.market_data = MarketDataService()
        self.ocbs_client = ocbs_client

    def reconcile_positions(self) -> Dict[str, Any]:
        """Reconcile internal positions with broker positions."""
        try:
            logger.info("Starting position reconciliation")

            # Get internal positions
            internal_cw, internal_hedge = load_portfolio()
            internal_positions = self._normalize_internal_positions(internal_cw, internal_hedge)

            # Get broker positions
            broker_positions = self._get_broker_positions()

            # Perform reconciliation
            reconciliation_result = self._compare_positions(internal_positions, broker_positions)

            # Record reconciliation event
            self._record_reconciliation_event(reconciliation_result)

            # Alert on discrepancies
            self._handle_discrepancies(reconciliation_result)

            logger.info(f"Reconciliation completed. Discrepancies: {len(reconciliation_result['discrepancies'])}")
            return reconciliation_result

        except (ValueError, TypeError, SQLAlchemyError, OCBSAPIError) as e:
            error_msg = f"Reconciliation failed: {e}"
            logger.error(error_msg)

            self._record_reconciliation_event({
                "status": "failed",
                "error": str(e),
                "discrepancies": []
            })

            raise ReconciliationError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected reconciliation error: {e}"
            logger.exception(error_msg)

            self._record_reconciliation_event({
                "status": "failed",
                "error": str(e),
                "discrepancies": []
            })

            raise ReconciliationError(error_msg) from e

    def reconcile_trades(self, days_back: int = 1) -> Dict[str, Any]:
        """Reconcile trades with broker for the last N days."""
        try:
            logger.info(f"Starting trade reconciliation for last {days_back} days")

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Get broker trades
            broker_trades = self.ocbs_client.get_account_trades(start_date, end_date)

            # Get internal trades from database
            internal_trades = self._get_internal_trades(start_date, end_date)

            # Compare trades
            reconciliation_result = self._compare_trades(internal_trades, broker_trades)

            # Record reconciliation event
            self._record_reconciliation_event(reconciliation_result, "trades")

            logger.info(f"Trade reconciliation completed. Unmatched: {len(reconciliation_result['unmatched_internal']) + len(reconciliation_result['unmatched_broker'])}")
            return reconciliation_result

        except Exception as e:
            error_msg = f"Trade reconciliation failed: {e}"
            logger.error(error_msg)
            raise ReconciliationError(error_msg)

    def _normalize_internal_positions(self, cw_positions: List, hedge_positions: List) -> Dict[str, Dict[str, Any]]:
        """Normalize internal positions to comparable format."""
        normalized = {}

        # Process CW positions (convert to equivalent underlying exposure)
        for cw in cw_positions:
            underlying = cw.underlying
            if underlying not in normalized:
                normalized[underlying] = {
                    "symbol": underlying,
                    "internal_quantity": 0,
                    "broker_quantity": 0,
                    "cw_positions": []
                }

            # CW positions represent short exposure (issuer sold equivalent shares)
            equivalent_quantity = -cw.cw_qty * cw.conversion_ratio
            normalized[underlying]["internal_quantity"] += equivalent_quantity
            normalized[underlying]["cw_positions"].append({
                "ticker": cw.ticker,
                "quantity": cw.cw_qty,
                "conversion_ratio": cw.conversion_ratio
            })

        # Process hedge positions
        for hedge in hedge_positions:
            underlying = hedge.underlying
            if underlying not in normalized:
                normalized[underlying] = {
                    "symbol": underlying,
                    "internal_quantity": 0,
                    "broker_quantity": 0,
                    "hedge_positions": []
                }

            normalized[underlying]["internal_quantity"] += hedge.shares
            normalized[underlying]["hedge_positions"].append({
                "shares": hedge.shares,
                "avg_price": hedge.avg_price
            })

        return normalized

    def _get_broker_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get positions from broker API."""
        try:
            broker_positions_raw = self.ocbs_client.get_account_positions()
            normalized = {}

            for pos in broker_positions_raw:
                symbol = pos.get("symbol")
                quantity = pos.get("quantity", 0)

                normalized[symbol] = {
                    "symbol": symbol,
                    "broker_quantity": quantity,
                    "broker_data": pos
                }

            return normalized

        except OCBSAPIError as e:
            logger.warning(f"Could not get broker positions: {e}")
            return {}

    def _compare_positions(self, internal: Dict[str, Dict], broker: Dict[str, Dict]) -> Dict[str, Any]:
        """Compare internal vs broker positions."""
        all_symbols = set(internal.keys()) | set(broker.keys())
        discrepancies = []

        for symbol in all_symbols:
            int_pos = internal.get(symbol, {"internal_quantity": 0})
            brk_pos = broker.get(symbol, {"broker_quantity": 0})

            internal_qty = int_pos["internal_quantity"]
            broker_qty = brk_pos["broker_quantity"]

            if abs(internal_qty - broker_qty) > 0.01:  # Allow small rounding differences
                discrepancies.append({
                    "symbol": symbol,
                    "internal_quantity": internal_qty,
                    "broker_quantity": broker_qty,
                    "difference": internal_qty - broker_qty,
                    "internal_cw_positions": int_pos.get("cw_positions", []),
                    "internal_hedge_positions": int_pos.get("hedge_positions", []),
                    "broker_data": brk_pos.get("broker_data", {})
                })

        return {
            "status": "completed",
            "reconciliation_time": datetime.now(),
            "total_symbols": len(all_symbols),
            "discrepancies": discrepancies,
            "matched_symbols": len(all_symbols) - len(discrepancies)
        }

    def _compare_trades(self, internal_trades: List[InternalTrade], broker_trades: List[BrokerTrade]) -> Dict[str, Any]:
        """Compare internal vs broker trades."""
        # This is a simplified implementation.
        # For production, use robust matching by trade ID, amount, side, and execution time windows.

        unmatched_internal = []
        unmatched_broker = []
        matched = []

        # Matching priority:
        # 1. trade_id match overrides all (best match)
        # 2. fallback to symbol + quantity + time tolerance

        for int_trade in internal_trades:
            match_found = False
            for brk_trade in broker_trades:
                internal_id = int_trade.get("trade_id")
                broker_id = brk_trade.get("trade_id")

                if internal_id and broker_id:
                    if internal_id == broker_id:
                        matched.append({"internal": int_trade, "broker": brk_trade})
                        match_found = True
                        break
                    else:
                        continue

                if (int_trade.get("underlying") == brk_trade.get("symbol") and
                    abs(int_trade.get("quantity", 0) - brk_trade.get("quantity", 0)) < 0.01 and
                    abs((int_trade.get("execution_time") - brk_trade.get("execution_time", datetime.now())).seconds) < 300):  # 5 min tolerance
                    matched.append({"internal": int_trade, "broker": brk_trade})
                    match_found = True
                    break

            if not match_found:
                unmatched_internal.append(int_trade)

        # Find unmatched broker trades
        matched_broker_ids = {m["broker"].get("trade_id") for m in matched}
        for brk_trade in broker_trades:
            if brk_trade.get("trade_id") not in matched_broker_ids:
                unmatched_broker.append(brk_trade)

        return {
            "status": "completed",
            "reconciliation_time": datetime.now(),
            "matched": matched,
            "unmatched_internal": unmatched_internal,
            "unmatched_broker": unmatched_broker
        }

    def _get_internal_trades(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get internal trades from database within date range."""
        session = get_db_session()
        try:
            from ..database.models import Trade
            trades = session.query(Trade).filter(
                Trade.execution_time >= start_date,
                Trade.execution_time <= end_date
            ).all()

            return [{
                "id": t.id,
                "trade_id": t.trade_id,
                "underlying": t.underlying,
                "quantity": t.quantity,
                "price": t.price,
                "execution_time": t.execution_time,
                "action": t.action.value
            } for t in trades]

        finally:
            session.close()

    def _record_reconciliation_event(self, result: Dict[str, Any], reconciliation_type: str = "positions") -> None:
        """Record reconciliation event."""
        session = get_db_session()
        try:
            summary = f"{reconciliation_type.title()} reconciliation {result['status']}"
            details = f"Time: {result['reconciliation_time']}, Status: {result['status']}"

            if reconciliation_type == "positions":
                details += f", Discrepancies: {len(result.get('discrepancies', []))}"
            else:
                details += f", Matched: {len(result.get('matched', []))}, Unmatched: {len(result.get('unmatched_internal', [])) + len(result.get('unmatched_broker', []))}"

            audit_event = AuditEvent(
                event_type=AuditEventType.RECONCILIATION,
                severity="info" if result["status"] == "completed" else "error",
                summary=summary,
                details=details,
                system_component="ReconciliationEngine",
                event_time=datetime.now()
            )
            session.add(audit_event)
            session.commit()

        except (SQLAlchemyError, ValueError, TypeError) as e:
            session.rollback()
            logger.error(f"Failed to record reconciliation event: {e}")
        except Exception as e:
            session.rollback()
            logger.exception(f"Unexpected failure recording reconciliation event: {e}")
        finally:
            session.close()

    def _handle_discrepancies(self, result: Dict[str, Any]) -> None:
        """Handle position discrepancies by sending alerts."""
        discrepancies = result.get("discrepancies", [])
        if not discrepancies:
            return

        # Send alert for significant discrepancies
        significant_discrepancies = [
            d for d in discrepancies
            if abs(d["difference"]) > 1000  # Threshold for alerting
        ]

        if significant_discrepancies:
            alert_message = f"Position Reconciliation Alert: {len(significant_discrepancies)} significant discrepancies found\n"
            for disc in significant_discrepancies[:5]:  # Limit to first 5
                alert_message += f"- {disc['symbol']}: Internal={disc['internal_quantity']:.0f}, Broker={disc['broker_quantity']:.0f}, Diff={disc['difference']:.0f}\n"

            alert_manager.send_alert(
                "Position Reconciliation Alert",
                alert_message
            )


# Global instance
reconciliation_engine = ReconciliationEngine()