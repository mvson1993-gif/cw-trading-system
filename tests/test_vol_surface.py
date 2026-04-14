import pytest
from cw_trading_system.models.vol_surface import VolSurface


class TestVolSurface:
    def test_init(self):
        vs = VolSurface()
        assert "HPG.VN" in vs.atm_vol
        assert "MWG.VN" in vs.atm_vol
        assert vs.skew_alpha == -0.25
        assert vs.curvature_beta == 0.40
        assert vs.term_gamma == 0.05

    def test_get_vol_atm(self):
        vs = VolSurface()
        vol = vs.get_vol("HPG.VN", 100, 100, 1)
        # ATM: m=1, skew=0, curvature=0, term=0.05
        expected = 0.30 + 0.05
        assert abs(vol - expected) < 1e-6

    def test_get_vol_itm(self):
        vs = VolSurface()
        vol = vs.get_vol("HPG.VN", 90, 100, 1)  # ITM
        m = 0.9
        skew = -0.25 * (0.9 - 1)  # positive
        curvature = 0.40 * (0.9 - 1)**2
        term = 0.05
        expected = 0.30 + skew + curvature + term
        assert abs(vol - expected) < 1e-6

    def test_get_vol_otm(self):
        vs = VolSurface()
        vol = vs.get_vol("HPG.VN", 110, 100, 1)  # OTM
        m = 1.1
        skew = -0.25 * (1.1 - 1)  # negative
        curvature = 0.40 * (1.1 - 1)**2
        term = 0.05
        expected = 0.30 + skew + curvature + term
        assert abs(vol - expected) < 1e-6

    def test_get_vol_unknown_ticker(self):
        vs = VolSurface()
        vol = vs.get_vol("UNKNOWN", 100, 100, 1)
        expected = 0.30 + 0.05  # default base
        assert abs(vol - expected) < 1e-6

    def test_get_vol_minimum(self):
        vs = VolSurface()
        # Set parameters to make vol negative
        vs.skew_alpha = -1.0
        vs.curvature_beta = 0.0
        vs.term_gamma = 0.0
        vol = vs.get_vol("HPG.VN", 200, 100, 1)  # Deep OTM
        assert vol >= 0.05  # Minimum vol