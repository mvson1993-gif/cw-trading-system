import pytest
import math
from cw_trading_system.models.black_scholes import norm_cdf, compute_d1, compute_d2, call_price


class TestBlackScholes:
    def test_norm_cdf(self):
        # Test standard normal CDF
        assert abs(norm_cdf(0) - 0.5) < 1e-6
        assert norm_cdf(1.96) > 0.975
        assert norm_cdf(-1.96) < 0.025

    def test_compute_d1(self):
        # Test d1 calculation
        d1 = compute_d1(100, 100, 1, 0.05, 0.2)
        expected = (math.log(1) + (0.05 + 0.5 * 0.04) * 1) / (0.2 * math.sqrt(1))
        assert abs(d1 - expected) < 1e-6

    def test_compute_d2(self):
        # Test d2 calculation
        d1 = compute_d1(100, 100, 1, 0.05, 0.2)
        d2 = compute_d2(d1, 0.2, 1)
        expected = d1 - 0.2 * math.sqrt(1)
        assert abs(d2 - expected) < 1e-6

    def test_call_price_atm(self):
        # Test ATM call price (approximate)
        price = call_price(100, 100, 1, 0.05, 0.2)
        # Expected ~10.33 for BS model
        assert 10.0 < price < 11.0

    def test_call_price_itm(self):
        # Test ITM call
        price = call_price(110, 100, 1, 0.05, 0.2)
        assert price > 10.33  # Should be higher than ATM

    def test_call_price_otm(self):
        # Test OTM call
        price = call_price(90, 100, 1, 0.05, 0.2)
        assert price < 10.33  # Should be lower than ATM

    def test_call_price_zero_time(self):
        # Test at expiry
        price = call_price(100, 100, 0, 0.05, 0.2)
        assert price == 0.0  # ATM at expiry

        price = call_price(110, 100, 0, 0.05, 0.2)
        assert price == 10.0  # ITM

    def test_call_price_zero_vol(self):
        # Test zero volatility
        price = call_price(100, 100, 1, 0.05, 0)
        expected = max(100 - 100 * math.exp(-0.05 * 1), 0)
        assert abs(price - expected) < 1e-6