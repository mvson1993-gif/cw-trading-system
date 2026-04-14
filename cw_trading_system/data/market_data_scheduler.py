# data/market_data_scheduler.py

import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .market_data import MarketDataService, MarketDataMonitor
from ..engine.monitoring_engine import monitoring_engine
from ..engine.reconciliation_engine import reconciliation_engine
from ..config.settings import BROKER_CONFIG
from ..utils.logging import get_logger

logger = get_logger(__name__)

class MarketDataScheduler:

    def __init__(self, tickers_to_monitor=None):
        self.market_data_service = MarketDataService()
        self.monitor = MarketDataMonitor(self.market_data_service)
        self.scheduler = BackgroundScheduler()
        self.tickers = tickers_to_monitor or ["HPG.VN", "MWG.VN"]
        self.is_running = False

    def start(self):
        """Start the background scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        # Add job to check market data every 5 minutes
        self.scheduler.add_job(
            func=self._check_market_data,
            trigger=IntervalTrigger(minutes=5),
            id='market_data_check',
            name='Market Data Health Check'
        )

        # Add job to refresh cache every 10 minutes
        self.scheduler.add_job(
            func=self._refresh_cache,
            trigger=IntervalTrigger(minutes=10),
            id='cache_refresh',
            name='Cache Refresh'
        )

        # Add job to monitor risk every 2 minutes
        self.scheduler.add_job(
            func=self._monitor_risk,
            trigger=IntervalTrigger(minutes=2),
            id='risk_monitoring',
            name='Risk Monitoring'
        )

        # Add job to reconcile positions every 24 hours
        if BROKER_CONFIG.reconciliation_enabled:
            self.scheduler.add_job(
                func=self._reconcile_positions,
                trigger=IntervalTrigger(hours=BROKER_CONFIG.reconciliation_interval_hours),
                id='position_reconciliation',
                name='Position Reconciliation'
            )

        self.scheduler.start()
        self.is_running = True
        logger.info("Market data scheduler started")

    def stop(self):
        """Stop the background scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Market data scheduler stopped")

    def _check_market_data(self):
        """Periodic health check for market data."""
        logger.info("Running market data health check")
        results = self.monitor.check_data_freshness(self.tickers)
        
        # Log results
        for ticker, info in results.items():
            if info['status'] == 'error':
                logger.error(f"Market data error for {ticker}: {info['error']}")
            else:
                logger.info(f"Market data OK for {ticker}: {info['spot']}")

    def _refresh_cache(self):
        """Refresh market data cache."""
        logger.info("Refreshing market data cache")
        for ticker in self.tickers:
            try:
                # This will fetch fresh data and update cache
                spot = self.market_data_service.get_spot(ticker)
                logger.debug(f"Refreshed cache for {ticker}: {spot}")
            except Exception as e:
                logger.error(f"Failed to refresh cache for {ticker}: {e}")

    def _monitor_risk(self):
        """Periodic risk monitoring and alerting."""
        logger.info("Running risk monitoring check")
        monitoring_engine.check_and_alert()

    def _reconcile_positions(self):
        """Periodic position reconciliation."""
        logger.info("Running position reconciliation")
        try:
            result = reconciliation_engine.reconcile_positions()
            discrepancies = result.get("discrepancies", [])
            if discrepancies:
                logger.warning(f"Position reconciliation found {len(discrepancies)} discrepancies")
            else:
                logger.info("Position reconciliation completed - all positions matched")
        except Exception as e:
            logger.error(f"Position reconciliation failed: {e}")

    def get_monitor_status(self):
        """Get current monitor status."""
        return {
            'is_running': self.is_running,
            'last_check': self.monitor.last_check,
            'market_alerts': self.monitor.get_alerts(),
            'risk_alerts': monitoring_engine.get_dashboard_alerts()
        }