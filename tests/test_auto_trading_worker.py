from unittest.mock import MagicMock

from cw_trading_system.engine.auto_trading_worker import AutoTradingWorker, TradingTask


def test_worker_start_and_stop():
    worker = AutoTradingWorker(market_data_service=MagicMock())

    started = worker.start()
    stopped = worker.stop()
    restarted = worker.start()

    assert started["status"] == "running"
    assert stopped["status"] == "stopped"
    assert restarted["status"] == "running"


def test_register_and_unregister_strategy():
    worker = AutoTradingWorker(market_data_service=MagicMock())

    task = TradingTask(
        ticker="HPG24001",
        underlying="HPG.VN",
        strike=30.0,
        expiry="2026-12-31",
    )

    registered = worker.register_strategy(task)
    assert registered["registered"] is True
    assert registered["task"]["ticker"] == "HPG24001"

    removed = worker.unregister_strategy("HPG24001", "HPG.VN")
    assert removed["removed"] is True


def test_run_cycle_generates_quote_and_simulated_orders():
    md = MagicMock()
    md.get_spot.return_value = 32.0
    md.get_vol.return_value = 0.35

    worker = AutoTradingWorker(market_data_service=md)
    task = TradingTask(
        ticker="HPG24001",
        underlying="HPG.VN",
        strike=30.0,
        expiry="2026-12-31",
        market_making_enabled=True,
        auto_hedging_enabled=False,
        quote_quantity=100000,
    )
    worker.register_strategy(task)

    result = worker.run_cycle("HPG24001", "HPG.VN")

    assert result["success"] is True
    assert result["quote_result"]["success"] is True
    assert len(result["quote_result"]["orders"]) == 2


def test_run_cycle_generates_hedge_decision_when_enabled():
    md = MagicMock()
    md.get_spot.return_value = 32.0
    md.get_vol.return_value = 0.35

    worker = AutoTradingWorker(market_data_service=md)
    task = TradingTask(
        ticker="HPG24001",
        underlying="HPG.VN",
        strike=30.0,
        expiry="2026-12-31",
        market_making_enabled=False,
        auto_hedging_enabled=True,
        delta_override=250000,
        delta_band=100000,
    )
    worker.register_strategy(task)

    result = worker.run_cycle("HPG24001", "HPG.VN")

    assert result["success"] is True
    assert result["hedge_result"]["success"] is True
    assert result["hedge_result"]["decision"]["requires_hedge"] is True
