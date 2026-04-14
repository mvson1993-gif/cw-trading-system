# tests/test_monitoring_engine.py

import pytest
from unittest.mock import patch, MagicMock
from cw_trading_system.engine.monitoring_engine import MonitoringEngine
from cw_trading_system.data.positions import Portfolio
from cw_trading_system.config.settings import RISK_LIMITS


@pytest.fixture
def monitoring_engine():
    return MonitoringEngine()


@pytest.fixture
def mock_portfolio():
    portfolio = MagicMock(spec=Portfolio)
    portfolio.cw_positions = []
    portfolio.get_hedge_dict.return_value = {}
    return portfolio


@pytest.fixture
def mock_market_data():
    md = MagicMock()
    md.get_spot.return_value = 100.0
    return md


def test_monitoring_engine_init(monitoring_engine):
    assert hasattr(monitoring_engine, 'market_data')
    assert hasattr(monitoring_engine, 'last_alert_times')
    assert monitoring_engine.last_alert_times == {}


@patch('cw_trading_system.engine.monitoring_engine.load_portfolio')
@patch('cw_trading_system.engine.monitoring_engine.calculate_portfolio_risk')
@patch('cw_trading_system.engine.monitoring_engine.calculate_pnl')
@patch('cw_trading_system.engine.monitoring_engine.record_snapshot')
@patch('cw_trading_system.engine.monitoring_engine.alert_manager')
def test_check_and_alert_no_breaches(mock_alert, mock_record, mock_pnl, mock_risk, mock_load, monitoring_engine, mock_portfolio):
    mock_load.return_value = ([], [])  # Return tuple of empty lists
    mock_risk.return_value = {"breaches": []}
    mock_pnl.return_value = {"total_pnl": 1000}

    monitoring_engine.check_and_alert()

    mock_load.assert_called_once()
    mock_risk.assert_called_once()
    mock_pnl.assert_called_once()
    mock_record.assert_called_once()
    mock_alert.send_alert.assert_not_called()


@patch('cw_trading_system.engine.monitoring_engine.load_portfolio')
@patch('cw_trading_system.engine.monitoring_engine.calculate_portfolio_risk')
@patch('cw_trading_system.engine.monitoring_engine.calculate_pnl')
@patch('cw_trading_system.engine.monitoring_engine.record_snapshot')
@patch('cw_trading_system.engine.monitoring_engine.alert_manager')
def test_check_and_alert_with_breaches(mock_alert, mock_record, mock_pnl, mock_risk, mock_load, monitoring_engine, mock_portfolio):
    mock_load.return_value = ([], [])
    risk_data = {
        "breaches": ["DELTA LIMIT BREACH"],
        "total": {"delta": 3000000, "gamma": 10000, "vega": 50000}
    }
    mock_risk.return_value = risk_data
    mock_pnl.return_value = {"total_pnl": 1000}

    monitoring_engine.check_and_alert()

    mock_alert.send_alert.assert_called_once()
    call_args = mock_alert.send_alert.call_args[0]
    assert "DELTA LIMIT BREACH" in call_args[0]
    assert "3000000" in call_args[1]


@patch('cw_trading_system.engine.monitoring_engine.load_portfolio')
@patch('cw_trading_system.engine.monitoring_engine.calculate_portfolio_risk')
def test_get_dashboard_alerts(mock_risk, mock_load, monitoring_engine, mock_portfolio):
    mock_load.return_value = ([], [])
    mock_risk.return_value = {"breaches": ["TEST BREACH"]}

    alerts = monitoring_engine.get_dashboard_alerts()

    assert alerts == ["TEST BREACH"]


@patch('cw_trading_system.engine.monitoring_engine.load_portfolio')
@patch('cw_trading_system.engine.monitoring_engine.calculate_portfolio_risk')
def test_get_dashboard_alerts_error(mock_risk, mock_load, monitoring_engine):
    mock_load.side_effect = Exception("Test error")

    alerts = monitoring_engine.get_dashboard_alerts()

    assert alerts == ["MONITORING SYSTEM ERROR"]