# engine/monitoring_engine.py

import logging
from datetime import datetime
from ..data.position_store import load_portfolio
from ..data.positions import Portfolio
from ..data.market_data import MarketDataService
from ..engine.risk_engine import calculate_portfolio_risk
from ..engine.pnl_engine import calculate_pnl
from ..data.monitor_store import record_snapshot
from ..utils.alerting import alert_manager
from ..config.settings import RISK_LIMITS
from ..errors import AppError

logger = logging.getLogger(__name__)


class MonitoringEngine:
    """Real-time risk monitoring and alerting engine."""

    def __init__(self):
        self.market_data = MarketDataService()
        self.last_alert_times = {}  # Track last alert time per breach type

    def check_and_alert(self):
        """Perform risk check and send alerts for breaches."""
        try:
            cw_positions, hedge_positions = load_portfolio()
            portfolio = Portfolio(cw_positions, hedge_positions)
            risk = calculate_portfolio_risk(portfolio, self.market_data)
            pnl = calculate_pnl(portfolio, self.market_data)

            # Record snapshot
            record_snapshot(risk, pnl)

            # Check for breaches
            breaches = risk.get("breaches", [])
            if breaches:
                self._handle_breaches(breaches, risk)

            logger.info(f"Monitoring check completed. Breaches: {breaches}")

        except (ValueError, TypeError, RuntimeError, PermissionError) as e:
            logger.error(f"Monitoring check failed: {e}")
            alert_manager.send_alert(
                "Monitoring System Error",
                f"Critical error in monitoring system: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected monitoring check failure: {e}")
            alert_manager.send_alert(
                "Monitoring System Error",
                f"Critical error in monitoring system: {str(e)}"
            )

    def _handle_breaches(self, breaches, risk):
        """Handle risk breaches by sending alerts."""
        current_time = datetime.now()

        for breach in breaches:
            # Check if we already alerted recently (avoid spam)
            last_alert = self.last_alert_times.get(breach)
            if last_alert and (current_time - last_alert).seconds < 300:  # 5 minutes
                continue

            # Send alert
            subject = f"RISK BREACH ALERT: {breach}"
            message = f"""
Risk Breach Detected: {breach}

Current Risk Metrics:
- Delta: {risk['total']['delta']:.2f} (Limit: ±{RISK_LIMITS.max_delta})
- Gamma: {risk['total']['gamma']:.2f} (Limit: ±{RISK_LIMITS.max_gamma})
- Vega: {risk['total']['vega']:.2f} (Limit: ±{RISK_LIMITS.max_vega})

Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()

            alert_manager.send_alert(subject, message)
            self.last_alert_times[breach] = current_time

    def get_dashboard_alerts(self):
        """Get current alerts for dashboard display."""
        try:
            cw_positions, hedge_positions = load_portfolio()
            portfolio = Portfolio(cw_positions, hedge_positions)
            risk = calculate_portfolio_risk(portfolio, self.market_data)
            breaches = risk.get("breaches", [])
            return breaches
        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(f"Failed to get dashboard alerts: {e}")
            return ["MONITORING SYSTEM ERROR"]
        except Exception as e:
            logger.exception(f"Unexpected failure getting dashboard alerts: {e}")
            return ["MONITORING SYSTEM ERROR"]


# Global instance
monitoring_engine = MonitoringEngine()