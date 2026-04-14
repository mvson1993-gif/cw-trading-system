# tests/test_reconciliation_engine.py

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from cw_trading_system.engine.reconciliation_engine import ReconciliationEngine, ReconciliationError


@pytest.fixture
def reconciliation_engine():
    return ReconciliationEngine()


@patch('cw_trading_system.engine.reconciliation_engine.load_portfolio')
@patch('cw_trading_system.engine.reconciliation_engine.ocbs_client')
@patch('cw_trading_system.engine.reconciliation_engine.get_db_session')
def test_reconcile_positions_success(mock_session, mock_client, mock_load, reconciliation_engine):
    # Mock internal positions
    mock_load.return_value = ([], [])  # Empty portfolio

    # Ensure engine uses mocked broker client for this test
    reconciliation_engine.ocbs_client = mock_client

    # Mock broker positions
    mock_client.get_account_positions.return_value = []

    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance

    result = reconciliation_engine.reconcile_positions()

    assert result["status"] == "completed"
    assert result["discrepancies"] == []
    assert result["matched_symbols"] == 0
    mock_client.get_account_positions.assert_called_once()


@patch('cw_trading_system.engine.reconciliation_engine.load_portfolio')
@patch('cw_trading_system.engine.reconciliation_engine.ocbs_client')
def test_reconcile_positions_with_discrepancies(mock_client, mock_load, reconciliation_engine):
    # Ensure engine uses mocked broker client for this test
    reconciliation_engine.ocbs_client = mock_client

    # Mock internal positions with HPG
    mock_cw = [MagicMock()]
    mock_cw[0].underlying = "HPG.VN"
    mock_cw[0].cw_qty = 1000000
    mock_cw[0].conversion_ratio = 1.0
    mock_cw[0].ticker = "HPG24001"

    mock_load.return_value = (mock_cw, [])

    # Mock broker positions - different quantity
    mock_client.get_account_positions.return_value = [
        {"symbol": "HPG.VN", "quantity": 500000}  # Half the expected
    ]

    result = reconciliation_engine.reconcile_positions()

    assert result["status"] == "completed"
    assert len(result["discrepancies"]) == 1
    disc = result["discrepancies"][0]
    assert disc["symbol"] == "HPG.VN"
    assert disc["internal_quantity"] == -1000000  # Short position
    assert disc["broker_quantity"] == 500000
    assert disc["difference"] == -1500000  # internal - broker


@patch('cw_trading_system.engine.reconciliation_engine.ocbs_client')
def test_reconcile_positions_broker_error(mock_client, reconciliation_engine):
    reconciliation_engine.ocbs_client = mock_client
    mock_client.get_account_positions.side_effect = Exception("API Error")

    with pytest.raises(ReconciliationError):
        reconciliation_engine.reconcile_positions()


@patch('cw_trading_system.engine.reconciliation_engine.ocbs_client')
@patch('cw_trading_system.engine.reconciliation_engine.get_db_session')
def test_reconcile_trades_success(mock_session, mock_client, reconciliation_engine):
    reconciliation_engine.ocbs_client = mock_client

    # Mock broker trades
    mock_client.get_account_trades.return_value = [
        {
            "trade_id": "B123",
            "symbol": "HPG.VN",
            "quantity": 1000000,
            "execution_time": datetime.now(),
            "price": 25.0
        }
    ]

    # Mock internal trades
    mock_session_instance = MagicMock()
    mock_trade = MagicMock()
    mock_trade.id = 1
    mock_trade.trade_id = "I123"
    mock_trade.underlying = "HPG.VN"
    mock_trade.quantity = 1000000
    mock_trade.price = 25.0
    mock_trade.execution_time = datetime.now()
    mock_trade.action.value = "BUY"

    mock_session_instance.query.return_value.filter.return_value.all.return_value = [mock_trade]
    mock_session.return_value = mock_session_instance

    result = reconciliation_engine.reconcile_trades(days_back=1)

    assert result["status"] == "completed"
    # Note: In this simple test, trades won't match due to different trade_ids
    assert len(result["unmatched_internal"]) == 1
    assert len(result["unmatched_broker"]) == 1
    assert len(result["matched"]) == 0


@patch('cw_trading_system.engine.reconciliation_engine.ocbs_client')
@patch('cw_trading_system.engine.reconciliation_engine.get_db_session')
def test_reconcile_trades_trade_id_match(mock_session, mock_client, reconciliation_engine):
    reconciliation_engine.ocbs_client = mock_client

    # Broker trade uses trade_id B123
    mock_client.get_account_trades.return_value = [
        {
            "trade_id": "B123",
            "symbol": "HPG.VN",
            "quantity": 1000000,
            "execution_time": datetime.now(),
            "price": 25.0
        }
    ]

    mock_session_instance = MagicMock()
    mock_trade = MagicMock()
    mock_trade.id = 1
    mock_trade.trade_id = "B123"
    mock_trade.underlying = "HPG.VN"
    mock_trade.quantity = 1000000
    mock_trade.price = 25.0
    mock_trade.execution_time = datetime.now()
    mock_trade.action.value = "BUY"

    mock_session_instance.query.return_value.filter.return_value.all.return_value = [mock_trade]
    mock_session.return_value = mock_session_instance

    result = reconciliation_engine.reconcile_trades(days_back=1)

    assert result["status"] == "completed"
    assert len(result["matched"]) == 1
    assert len(result["unmatched_internal"]) == 0
    assert len(result["unmatched_broker"]) == 0


@patch('cw_trading_system.engine.reconciliation_engine.ocbs_client')
def test_reconcile_trades_broker_error(mock_client, reconciliation_engine):
    mock_client.get_account_trades.side_effect = Exception("API Error")

    with pytest.raises(ReconciliationError):
        reconciliation_engine.reconcile_trades(days_back=1)


def test_normalize_internal_positions(reconciliation_engine):
    # Test CW positions
    cw_positions = [
        MagicMock(underlying="HPG.VN", cw_qty=1000000, conversion_ratio=1.0, ticker="HPG24001")
    ]
    hedge_positions = []

    normalized = reconciliation_engine._normalize_internal_positions(cw_positions, hedge_positions)

    assert "HPG.VN" in normalized
    assert normalized["HPG.VN"]["internal_quantity"] == -1000000  # Short position
    assert len(normalized["HPG.VN"]["cw_positions"]) == 1

    # Test hedge positions
    cw_positions = []
    hedge_positions = [
        MagicMock(underlying="VNM.VN", shares=500000, avg_price=100.0)
    ]

    normalized = reconciliation_engine._normalize_internal_positions(cw_positions, hedge_positions)

    assert "VNM.VN" in normalized
    assert normalized["VNM.VN"]["internal_quantity"] == 500000
    assert len(normalized["VNM.VN"]["hedge_positions"]) == 1


def test_get_broker_positions(reconciliation_engine):
    broker_raw = [
        {"symbol": "AAPL", "quantity": 1000},
        {"symbol": "GOOGL", "quantity": -500}
    ]

    with patch.object(reconciliation_engine.ocbs_client, 'get_account_positions', return_value=broker_raw):
        positions = reconciliation_engine._get_broker_positions()

        assert "AAPL" in positions
        assert positions["AAPL"]["broker_quantity"] == 1000
        assert "GOOGL" in positions
        assert positions["GOOGL"]["broker_quantity"] == -500


def test_compare_positions(reconciliation_engine):
    internal = {
        "HPG.VN": {"internal_quantity": -1000000},
        "VNM.VN": {"internal_quantity": 500000}
    }
    broker = {
        "HPG.VN": {"broker_quantity": -1000000},
        "VNM.VN": {"broker_quantity": 600000}
    }

    result = reconciliation_engine._compare_positions(internal, broker)

    assert result["status"] == "completed"
    assert len(result["discrepancies"]) == 1  # Only VNM has discrepancy
    assert result["discrepancies"][0]["symbol"] == "VNM.VN"
    assert result["discrepancies"][0]["difference"] == -100000