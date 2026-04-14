# CW Trading System

A production-ready covered warrants trading system built incrementally through 4 phases.

## Architecture Overview

- **Database Layer**: SQLAlchemy ORM with SQLite backend
- **Data Layer**: Repository pattern for data persistence
- **Engine Layer**: Risk, P&L, pricing, and monitoring engines
- **Service Layer**: Market data integration with caching
- **UI Layer**: Streamlit dashboard for monitoring and trading

## Development Phases

### ✅ Phase 1: Foundation & State Management
- Database setup with SQLAlchemy ORM
- Repository pattern implementation
- Logging infrastructure
- Position and trade management
- **Status**: Complete (62 tests passing)

### ✅ Phase 2: Market Data Integration
- Yahoo Finance API integration
- Data caching with TTL
- Background scheduling with APScheduler
- Market data monitoring and health checks
- **Status**: Complete (76 tests passing)

### ✅ Phase 3: Monitoring & Alerting
- Real-time risk monitoring engine
- Email and SMS alerting system (configurable)
- Dashboard alerts integration
- Background risk monitoring jobs
- **Status**: Complete (76 tests passing)

### ✅ Phase 5: VN Market Data & Real-time APIs
- VNDirect, SSI, FTS API integration for reliable VN market data
- WebSocket real-time streaming for continuous price updates
- Provider fallback chain: VN APIs → Yahoo Finance → Mock data
- **Status**: Complete (WebSocket streaming, VN API clients ready)

### ✅ Phase 6: CW Data Framework & Banking APIs
- Covered Warrant data framework (ready for issuer APIs)
- Banking API integration (Vietcombank, Techcombank, Vietinbank)
- Capital management and settlement monitoring
- Margin health monitoring and alerts
- **Status**: Framework complete, APIs ready for credentials

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```bash
# Database
DATABASE_URL=sqlite:///./cw_trading_system.db

# VN Market Data APIs (Phase 5)
VNDIRECT_ENABLED=true
VNDIRECT_BASE_URL=https://api.vndirect.com.vn
VNDIRECT_API_KEY=your-vndirect-key
VNDIRECT_API_SECRET=your-vndirect-secret

SSI_ENABLED=true
SSI_BASE_URL=https://api.ssi.com.vn
SSI_API_KEY=your-ssi-key
SSI_API_SECRET=your-ssi-secret

# Real-time Streaming
WEBSOCKET_ENABLED=true
WEBSOCKET_URL=wss://websocket.vndirect.com.vn

# CW Data Framework (Phase 6)
CW_DATA_ENABLED=true
EXCHANGE_CW_ENABLED=true

# Banking APIs (Phase 6)
VCB_ENABLED=true
VCB_BASE_URL=https://api.vietcombank.com.vn
VCB_API_KEY=your-vcb-key
VCB_API_SECRET=your-vcb-secret
VCB_ACCOUNT_NUMBER=your-account

# Alerting (optional)
EMAIL_ENABLED=true
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=alerts@company.com
SMS_ENABLED=false
```

3. Run the dashboard:
```bash
streamlit run cw_trading_system/app.py
```

## Testing

Run the full test suite:
```bash
pytest tests/
```

## Configuration

Key settings in `cw_trading_system/config/settings.py`:
- Risk limits (delta, gamma, vega)
- Hedging policy
- Market assumptions
- Alerting configuration
- **Phase 4**: Broker API settings (OCBS credentials, reconciliation intervals)

Environment variables in `.env`:
```bash
# Broker API (Phase 4)
OCBS_ENABLED=false
OCBS_BASE_URL=https://api.ocbs.com
OCBS_API_KEY=your-ocbs-api-key
OCBS_API_SECRET=your-ocbs-api-secret
RECONCILIATION_ENABLED=false
RECONCILIATION_INTERVAL_HOURS=24
```

## Project Structure

```
cw_trading_system/
├── app.py                 # Streamlit dashboard
├── config/
│   └── settings.py        # Configuration management
├── brokers/
│   └── ocbs_client.py        # OCBS API client
├── data/
│   ├── market_data.py        # Market data service
│   ├── market_data_scheduler.py  # Background jobs
│   ├── monitor_store.py      # Monitoring data persistence
│   ├── position_store.py     # Position management
│   └── repositories/         # Repository pattern
├── engine/
│   ├── trade_execution_engine.py  # Trade execution
│   ├── reconciliation_engine.py   # Position reconciliation
│   ├── monitoring_engine.py   # Risk monitoring & alerts
│   ├── risk_engine.py         # Risk calculations
│   ├── pnl_engine.py          # P&L calculations
│   └── ...
├── models/                # SQLAlchemy models
├── utils/
│   ├── alerting.py        # Email/SMS alerts
│   └── logging.py         # Logging setup
└── tests/                 # Comprehensive test suite
```