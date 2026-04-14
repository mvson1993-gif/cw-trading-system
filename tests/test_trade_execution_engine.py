# tests/test_trade_execution_engine.py

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from cw_trading_system.engine.trade_execution_engine import TradeExecutionEngine, TradeExecutionError


@pytest.fixture
def trade_engine():
    return TradeExecutionEngine()


@patch('cw_trading_system.engine.trade_execution_engine.ocbs_client')
@patch('cw_trading_system.engine.trade_execution_engine.get_db_session')
def test_execute_cw_issuance_success(mock_session, mock_client):
    mock_client.place_order.return_value = {
        "order_id": "12345",
        "execution_price": 29.50
    }

    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance

    engine = TradeExecutionEngine()
    cw_data = {
        "ticker": "HPG24001",
        "underlying": "HPG.VN",
        "cw_qty": 1000000,
        "strike": 30.0,
        "expiry": "2024-12-31",
        "conversion_ratio": 1.0,
        "issue_price": 0.5
    }

    result = engine.execute_cw_issuance(cw_data)

    assert result["success"] is True
    assert result["order_id"] == "12345"
    assert result["execution_price"] == 29.50
    mock_client.place_order.assert_called_once()


@patch('cw_trading_system.engine.trade_execution_engine.ocbs_client')
def test_execute_cw_issuance_missing_field(mock_client):
    engine = TradeExecutionEngine()
    cw_data = {
        "ticker": "HPG24001",
        # missing underlying
        "cw_qty": 1000000,
        "strike": 30.0,
        "expiry": "2024-12-31"
    }

    with pytest.raises(ValueError, match="Missing required field: underlying"):
        engine.execute_cw_issuance(cw_data)


@patch('cw_trading_system.engine.trade_execution_engine.ocbs_client')
def test_execute_cw_issuance_api_error(mock_client):
    mock_client.place_order.side_effect = Exception("API Error")

    engine = TradeExecutionEngine()
    cw_data = {
        "ticker": "HPG24001",
        "underlying": "HPG.VN",
        "cw_qty": 1000000,
        "strike": 30.0,
        "expiry": "2024-12-31",
        "conversion_ratio": 1.0,
        "issue_price": 0.5
    }

    with pytest.raises(TradeExecutionError):
        engine.execute_cw_issuance(cw_data)


@patch('cw_trading_system.engine.trade_execution_engine.ocbs_client')
@patch('cw_trading_system.engine.trade_execution_engine.get_db_session')
def test_execute_hedge_trade_success(mock_session, mock_client):
    mock_client.place_order.return_value = {
        "order_id": "67890",
        "execution_price": 25.0
    }

    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance

    engine = TradeExecutionEngine()
    hedge_data = {
        "underlying": "HPG.VN",
        "side": "buy",
        "quantity": 1000000,
        "reason": "Delta hedging"
    }

    result = engine.execute_hedge_trade(hedge_data)

    assert result["success"] is True
    assert result["order_id"] == "67890"
    mock_client.place_order.assert_called_once()


@patch('cw_trading_system.engine.trade_execution_engine.ocbs_client')
def test_execute_hedge_trade_missing_field(mock_client):
    engine = TradeExecutionEngine()
    hedge_data = {
        "underlying": "HPG.VN",
        # missing side
        "quantity": 1000000
    }

    with pytest.raises(ValueError, match="Missing required field: side"):
        engine.execute_hedge_trade(hedge_data)


@patch('cw_trading_system.engine.trade_execution_engine.ocbs_client')
@patch('cw_trading_system.engine.trade_execution_engine.get_db_session')
def test_cancel_order_success(mock_session, mock_client):
    mock_client.cancel_order.return_value = {"status": "cancelled"}

    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance

    engine = TradeExecutionEngine()
    result = engine.cancel_order("12345")

    assert result == {"status": "cancelled"}
    mock_client.cancel_order.assert_called_once_with("12345")


@patch('cw_trading_system.engine.trade_execution_engine.ocbs_client')
def test_cancel_order_error(mock_client):
    mock_client.cancel_order.side_effect = Exception("Cancel failed")

    engine = TradeExecutionEngine()

    with pytest.raises(TradeExecutionError):
        engine.cancel_order("12345")