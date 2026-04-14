import pytest

from cw_trading_system.engine.market_making_engine import (
    MarketMakingEngine,
    TradingMode,
    StrategyStatus,
)


@pytest.fixture
def mm_engine():
    return MarketMakingEngine()


def test_build_two_sided_quote(mm_engine):
    quote = mm_engine.build_two_sided_quote(
        ticker="HPG24001",
        underlying="HPG.VN",
        fair_value=1.25,
        iv_premium=0.10,
        spread_pct=0.04,
        quantity=100000,
        inventory=25000,
    )

    assert quote["ticker"] == "HPG24001"
    assert quote["underlying"] == "HPG.VN"
    assert quote["bid_price"] < quote["ask_price"]
    assert quote["bid_quantity"] == 100000
    assert quote["ask_quantity"] < 100000  # inventory skews sell size down
    assert quote["mode"] == TradingMode.MANUAL.value


def test_market_making_workflow_lifecycle(mm_engine):
    started = mm_engine.set_market_making_mode(
        ticker="HPG24001",
        mode=TradingMode.AUTO,
        enabled=True,
    )
    stopped = mm_engine.set_market_making_mode(
        ticker="HPG24001",
        mode=TradingMode.AUTO,
        enabled=False,
    )

    assert started["status"] == StrategyStatus.RUNNING.value
    assert started["mode"] == TradingMode.AUTO.value
    assert stopped["status"] == StrategyStatus.STOPPED.value


def test_evaluate_hedge_need_sell(mm_engine):
    decision = mm_engine.evaluate_hedge_need(
        underlying="HPG.VN",
        net_delta=250000,
        delta_band=100000,
        hedge_ratio=1.0,
        min_trade_size=10000,
    )

    assert decision["requires_hedge"] is True
    assert decision["side"] == "sell"
    assert decision["quantity"] == 250000


def test_evaluate_hedge_need_no_trade_when_inside_band(mm_engine):
    decision = mm_engine.evaluate_hedge_need(
        underlying="HPG.VN",
        net_delta=75000,
        delta_band=100000,
        hedge_ratio=1.0,
        min_trade_size=10000,
    )

    assert decision["requires_hedge"] is False
    assert decision["status"] == StrategyStatus.IDLE.value
