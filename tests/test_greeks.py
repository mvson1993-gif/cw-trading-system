import pytest
import math
from cw_trading_system.models.greeks import norm_pdf, compute_greeks


class TestGreeks:
    def test_norm_pdf(self):
        # Test normal PDF at 0
        pdf = norm_pdf(0)
        expected = 1.0 / math.sqrt(2 * math.pi)
        assert abs(pdf - expected) < 1e-6

    def test_compute_greeks_atm(self):
        # Test Greeks for ATM option
        greeks = compute_greeks(100, 100, 1, 0.05, 0.2)
        assert "delta" in greeks
        assert "gamma" in greeks
        assert "vega" in greeks
        assert "theta" in greeks
        # ATM delta ~0.64 for these params
        assert 0.6 < greeks["delta"] < 0.7
        assert greeks["gamma"] > 0
        assert greeks["vega"] > 0
        assert greeks["theta"] < 0  # Theta is negative for long options

    def test_compute_greeks_itm(self):
        # Test ITM option
        greeks = compute_greeks(110, 100, 1, 0.05, 0.2)
        assert greeks["delta"] > 0.6  # Higher delta for ITM

    def test_compute_greeks_otm(self):
        # Test OTM option
        greeks = compute_greeks(90, 100, 1, 0.05, 0.2)
        assert greeks["delta"] < 0.5  # Lower delta for OTM

    def test_compute_greeks_zero_time(self):
        # Test at expiry
        greeks = compute_greeks(100, 100, 0, 0.05, 0.2)
        assert greeks["delta"] == 0.0  # OTM
        assert greeks["gamma"] == 0.0
        assert greeks["vega"] == 0.0
        assert greeks["theta"] == 0.0

        greeks = compute_greeks(110, 100, 0, 0.05, 0.2)
        assert greeks["delta"] == 1.0  # ITM

    def test_compute_greeks_zero_vol(self):
        # Test zero volatility
        greeks = compute_greeks(100, 100, 1, 0.05, 0)
        assert greeks["delta"] == 0.0  # OTM
        assert greeks["gamma"] == 0.0
        assert greeks["vega"] == 0.0
        assert greeks["theta"] == 0.0