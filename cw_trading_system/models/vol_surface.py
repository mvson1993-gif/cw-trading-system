# models/vol_surface.py

class VolSurface:

    def __init__(self):

        # ATM vol per underlying
        self.atm_vol = {
            "HPG.VN": 0.30,
            "MWG.VN": 0.35
        }

        # skew parameters (tunable)
        self.skew_alpha = -0.25     # slope
        self.curvature_beta = 0.40  # smile
        self.term_gamma = 0.05      # term structure

    def get_vol(self, ticker, strike, spot, T):

        base = self.atm_vol.get(ticker, 0.30)

        m = strike / spot  # moneyness

        skew = self.skew_alpha * (m - 1)
        curvature = self.curvature_beta * (m - 1) ** 2
        term = self.term_gamma * T

        vol = base + skew + curvature + term

        return max(vol, 0.05)
