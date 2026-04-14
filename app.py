import os
import sys

# Ensure package root is on import path when running from repository root
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from cw_trading_system.app import *
