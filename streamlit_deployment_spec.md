# Streamlit Deployment Design Spec for CW Trading System

## Overview
This spec outlines the design for deploying the CW Trading System as a Streamlit application for institutional covered warrants issuers. The deployment focuses on real-time risk management, trade execution, and monitoring with production-ready fault handling and observability.

## Modules

### Core Application Module
- **streamlit_app.py** (New): Main Streamlit application entry point
  - Imports: `streamlit`, `cw_trading_system.*`
  - Components: Dashboard, trade input forms, risk displays, monitoring panels
  - Code Hook: [cw_trading_system/streamlit_app.py](cw_trading_system/streamlit_app.py) (to be created)

### Engine Modules
- **Risk Engine**: [cw_trading_system/engine/risk_engine.py](cw_trading_system/engine/risk_engine.py)
  - Decorated with `@timed('risk_calculation')` for performance monitoring
  - Key Function: `calculate_portfolio_risk(positions, market_data)`
- **PnL Engine**: [cw_trading_system/engine/pnl_engine.py](cw_trading_system/engine/pnl_engine.py)
  - Decorated with `@timed('pnl_calculation')`
  - Key Function: `calculate_pnl(trades, positions, market_data)`
- **Trade Execution Engine**: [cw_trading_system/engine/trade_execution_engine.py](cw_trading_system/engine/trade_execution_engine.py)
  - Handles broker integration (OCBS mock/real)
  - Key Function: `execute_trade(order_details)`
- **Reconciliation Engine**: [cw_trading_system/engine/reconciliation_engine.py](cw_trading_system/engine/reconciliation_engine.py)
  - Matches trades with broker confirmations
  - Key Function: `reconcile_trades(session_alias)`

### Data Modules
- **Position Store**: [cw_trading_system/data/position_store.py](cw_trading_system/data/position_store.py)
  - JSON-based storage with DB fallback
  - Key Function: `save_positions(positions)`
- **Trade Store**: [cw_trading_system/data/trade_store.py](cw_trading_system/data/trade_store.py)
  - Stores executed trades
  - Key Function: `record_trade(trade)`
- **Market Data**: [cw_trading_system/data/market_data.py](cw_trading_system/data/market_data.py)
  - Decorated with `@timed('market_data_fetch')`
  - Key Functions: `get_spot(ticker)`, `get_vol(ticker, strike, expiry)`

### Configuration Module
- **Settings**: [cw_trading_system/config/settings.py](cw_trading_system/config/settings.py)
  - Environment-based config (dev/prod)
  - Includes API keys, DB connections, risk limits

### Utility Modules
- **Performance Utils**: [cw_trading_system/utils/performance.py](cw_trading_system/utils/performance.py)
  - `@timed` decorator for metrics collection
- **Error Handling**: [cw_trading_system/errors.py](cw_trading_system/errors.py)
  - Custom exceptions: `AppError`, `BrokerError`, `ReconciliationError`
- **Helpers**: [cw_trading_system/utils/helpers.py](cw_trading_system/utils/helpers.py)
  - Utility functions for calculations and formatting

## Dataflow

1. **User Input** → Streamlit UI forms collect trade orders, risk queries, or monitoring requests
2. **Validation** → Input validated using helpers.py functions and config limits
3. **Processing** → Route to appropriate engine:
   - Risk queries → risk_engine.calculate_portfolio_risk()
   - Trade execution → trade_execution_engine.execute_trade() → broker API
   - PnL calculation → pnl_engine.calculate_pnl()
4. **Data Persistence** → Results stored via position_store.py/trade_store.py
5. **Reconciliation** → reconciliation_engine.reconcile_trades() matches broker confirmations
6. **Display** → Streamlit renders results, charts, and alerts in real-time

## Fault-Handling

### Exception Hierarchy
- Base: `AppError` from [cw_trading_system/errors.py](cw_trading_system/errors.py)
- Specialized: `BrokerError`, `TradeExecutionError`, `ReconciliationError`, `RiskCalculationError`

### Error Handling Strategy
- **UI Layer**: Try-except in streamlit_app.py displays user-friendly error messages via `st.error()`
- **Engine Layer**: Engines raise domain-specific exceptions, logged via Python logging
- **Recovery**: Automatic retries for transient broker errors (configurable in settings.py)
- **Fallbacks**: JSON storage fallback if DB fails; cached market data if API unavailable

### Code Hooks
- Error catching: `try: result = engine.function() except AppError as e: st.error(str(e))`
- Logging: `import logging; logger = logging.getLogger(__name__)` in all modules

## Monitoring Map

### Performance Metrics
- **Decorators**: All critical functions use `@timed(label)` from performance.py
- **Metrics Collected**: Execution time, call count, error rates
- **Storage**: Logged to monitor_log.json via monitor_store.py

### Real-Time Dashboard
- **Streamlit Panels**: 
  - Risk metrics display (VaR, Greeks)
  - PnL charts with historical data
  - Trade status and reconciliation alerts
- **Alerts**: Color-coded warnings for breaches (e.g., risk limits exceeded)

### Observability
- **Logging Levels**: INFO for operations, ERROR for faults
- **Health Checks**: Streamlit sidebar shows system status (DB connection, broker API)
- **Audit Trail**: All trades and calculations logged with timestamps

### Code Hooks
- Dashboard update: `st.metric("Portfolio Risk", risk_value)` in streamlit_app.py
- Alert logic: `if risk > config.RISK_LIMIT: st.warning("Risk limit breached")`
- Monitoring data: `monitor_store.log_metric('risk_calc_time', duration)`