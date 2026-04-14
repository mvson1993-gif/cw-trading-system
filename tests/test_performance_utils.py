import pytest
import time
from cw_trading_system.utils.performance import timed


@timed("test_simple_timer")
def fast_func(x):
    return x * 2


def test_timed_decorator_returns_value():
    assert fast_func(5) == 10


def test_timed_decorator_logs_duration(caplog):
    caplog.set_level("DEBUG", logger="cw_trading_system.performance")

    @timed("timer_test")
    def slow_function():
        time.sleep(0.001)
        return True

    result = slow_function()

    assert result is True
    assert any("timer_test executed in" in rec.message for rec in caplog.records)
