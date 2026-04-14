# cw_trading_system/__main__.py
"""
Entry point for running the CW Trading System application.

Usage:
    python -m cw_trading_system
"""

import sys
import subprocess

if __name__ == "__main__":
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "cw_trading_system/app.py"
    ])
