# engine/trade_execution_engine.py

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.exc import SQLAlchemyError
from ..brokers.ocbs_client import ocbs_client, OCBSAPIError
from ..data.position_store import load_portfolio, save_portfolio
from ..data.trade_store import record_trade
from ..database.models import Trade, TradeAction, AuditEvent, AuditEventType
from ..database import get_session
# backwards compatibility for tests and helpers
from ..database import get_session as get_db_session
from ..utils.logging import get_logger
from ..utils.alerting import alert_manager
from ..config.settings import BROKER_CONFIG

logger = get_logger(__name__)


class TradeExecutionError(Exception):
    """Trade execution error."""
    pass


class TradeExecutionEngine:
    """Engine for executing trades through OCBS API."""

    def __init__(self):
        self.ocbs_client = ocbs_client

    def execute_cw_issuance(self, cw_position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CW issuance trade."""
        try:
            # Validate required fields
            required_fields = ["underlying", "ticker", "cw_qty", "strike", "expiry", "issue_price"]
            for field in required_fields:
                if field not in cw_position_data:
                    raise ValueError(f"Missing required field: {field}")

            # For CW issuance, we need to sell the underlying equivalent
            # This is a simplified implementation - in reality, this would involve
            # complex order routing and market making logic

            order_data = {
                "symbol": cw_position_data["underlying"],
                "side": "sell",  # Issuer sells equivalent shares
                "quantity": cw_position_data["cw_qty"] * cw_position_data.get("conversion_ratio", 1),
                "order_type": "market",
                "time_in_force": "day"
            }

            # Execute the order
            order_response = self.ocbs_client.place_order(order_data)

            # Record the trade
            trade_record = {
                "trade_id": order_response.get("order_id"),
                "action": TradeAction.SELL,
                "underlying": cw_position_data["underlying"],
                "quantity": order_data["quantity"],
                "price": order_response.get("execution_price", cw_position_data["issue_price"]),
                "execution_time": datetime.now(),
                "trade_value": order_data["quantity"] * order_response.get("execution_price", cw_position_data["issue_price"]),
                "fees": order_response.get("fees", 0),
                "notional_value": order_data["quantity"] * order_response.get("execution_price", cw_position_data["issue_price"]),
                "status": "filled",
                "counterparty": "OCBS",
                "broker_trade_id": order_response.get("order_id"),
                "notes": f"CW Issuance: {cw_position_data['ticker']}"
            }

            # Save to database
            self._record_trade_to_db(trade_record)

            # Record audit event
            self._record_audit_event(
                event_type=AuditEventType.TRADE_EXECUTED,
                summary=f"CW Issuance executed: {cw_position_data['ticker']}",
                details=f"Order ID: {order_response.get('order_id')}, Quantity: {order_data['quantity']}",
                trade_id=trade_record.get("id")
            )

            logger.info(f"CW issuance executed: {cw_position_data['ticker']}")
            return {
                "success": True,
                "order_id": order_response.get("order_id"),
                "execution_price": order_response.get("execution_price"),
                "trade_record": trade_record
            }

        except ValueError:
            # Validation errors should be propagated unwrapped for callers to handle specifically
            raise
        except (OCBSAPIError, SQLAlchemyError, RuntimeError) as e:
            error_msg = f"CW issuance failed: {e}"
            logger.error(error_msg)

            # Record failed trade
            self._record_audit_event(
                event_type=AuditEventType.TRADE_FAILED,
                summary=f"CW Issuance failed: {cw_position_data.get('ticker', 'Unknown')}",
                details=str(e),
                severity="error"
            )

            raise TradeExecutionError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected CW issuance error: {e}"
            logger.exception(error_msg)
            self._record_audit_event(
                event_type=AuditEventType.TRADE_FAILED,
                summary=f"CW Issuance failed: {cw_position_data.get('ticker', 'Unknown')}",
                details=str(e),
                severity="error"
            )
            raise TradeExecutionError(error_msg) from e

    def execute_hedge_trade(self, hedge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hedge trade."""
        try:
            required_fields = ["underlying", "side", "quantity", "reason"]
            for field in required_fields:
                if field not in hedge_data:
                    raise ValueError(f"Missing required field: {field}")

            order_data = {
                "symbol": hedge_data["underlying"],
                "side": hedge_data["side"],  # "buy" or "sell"
                "quantity": hedge_data["quantity"],
                "order_type": "market",
                "time_in_force": "day"
            }

            # Execute the order
            order_response = self.ocbs_client.place_order(order_data)

            # Determine trade action
            action = TradeAction.HEDGE_BUY if hedge_data["side"] == "buy" else TradeAction.HEDGE_SELL

            # Record the trade
            trade_record = {
                "trade_id": order_response.get("order_id"),
                "action": action,
                "underlying": hedge_data["underlying"],
                "quantity": hedge_data["quantity"],
                "price": order_response.get("execution_price", 0),
                "execution_time": datetime.now(),
                "trade_value": hedge_data["quantity"] * order_response.get("execution_price", 0),
                "fees": order_response.get("fees", 0),
                "notional_value": hedge_data["quantity"] * order_response.get("execution_price", 0),
                "status": "filled",
                "counterparty": "OCBS",
                "broker_trade_id": order_response.get("order_id"),
                "notes": f"Hedge trade: {hedge_data['reason']}"
            }

            # Save to database
            self._record_trade_to_db(trade_record)

            # Record audit event
            self._record_audit_event(
                event_type=AuditEventType.TRADE_EXECUTED,
                summary=f"Hedge trade executed: {hedge_data['underlying']} {hedge_data['side']}",
                details=f"Order ID: {order_response.get('order_id')}, Quantity: {hedge_data['quantity']}, Reason: {hedge_data['reason']}",
                trade_id=trade_record.get("id")
            )

            logger.info(f"Hedge trade executed: {hedge_data['underlying']} {hedge_data['side']}")
            return {
                "success": True,
                "order_id": order_response.get("order_id"),
                "execution_price": order_response.get("execution_price"),
                "trade_record": trade_record
            }

        except ValueError:
            # Validation errors should be propagated unwrapped for callers to handle specifically
            raise
        except (OCBSAPIError, SQLAlchemyError, RuntimeError) as e:
            error_msg = f"Hedge trade failed: {e}"
            logger.error(error_msg)

            self._record_audit_event(
                event_type=AuditEventType.TRADE_FAILED,
                summary=f"Hedge trade failed: {hedge_data.get('underlying', 'Unknown')}",
                details=str(e),
                severity="error"
            )

            raise TradeExecutionError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected hedge trade error: {e}"
            logger.exception(error_msg)

            self._record_audit_event(
                event_type=AuditEventType.TRADE_FAILED,
                summary=f"Hedge trade failed: {hedge_data.get('underlying', 'Unknown')}",
                details=str(e),
                severity="error"
            )

            raise TradeExecutionError(error_msg) from e

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a pending order."""
        try:
            cancel_response = self.ocbs_client.cancel_order(order_id)

            self._record_audit_event(
                event_type=AuditEventType.TRADE_EXECUTED,
                summary=f"Order cancelled: {order_id}",
                details=f"Cancel response: {cancel_response}"
            )

            logger.info(f"Order cancelled: {order_id}")
            return cancel_response

        except (OCBSAPIError, RuntimeError) as e:
            error_msg = f"Order cancellation failed: {e}"
            logger.error(error_msg)
            raise TradeExecutionError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected order cancellation error: {e}"
            logger.exception(error_msg)
            raise TradeExecutionError(error_msg) from e

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of an order."""
        try:
            return self.ocbs_client.get_order_status(order_id)
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            raise

    def _record_trade_to_db(self, trade_data: Dict[str, Any]) -> int:
        """Record trade to database."""
        session = get_db_session()
        try:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            trade_id = trade.id
            logger.info(f"Trade recorded to database: ID {trade_id}")
            return trade_id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record trade to database: {e}")
            raise
        finally:
            session.close()

    def _record_audit_event(self, event_type: AuditEventType, summary: str,
                           details: Optional[str] = None, severity: str = "info",
                           trade_id: Optional[int] = None) -> None:
        """Record audit event."""
        session = get_db_session()
        try:
            audit_event = AuditEvent(
                event_type=event_type,
                severity=severity,
                summary=summary,
                details=details,
                trade_id=trade_id,
                system_component="TradeExecutionEngine",
                event_time=datetime.now()
            )
            session.add(audit_event)
            session.commit()
            logger.debug(f"Audit event recorded: {summary}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record audit event: {e}")
        finally:
            session.close()


# Global instance
trade_execution_engine = TradeExecutionEngine()