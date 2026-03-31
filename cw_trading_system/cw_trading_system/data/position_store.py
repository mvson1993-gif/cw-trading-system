# data/position_store.py

import json
from datetime import date
from data.positions import CWPosition, HedgePosition

FILE_PATH = "data/positions.json"


# =========================
# LOAD
# =========================

def load_portfolio():

    try:
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return [], []

    cw_positions = [
        CWPosition(**p) for p in data.get("cw_positions", [])
    ]

    hedge_positions = [
        HedgePosition(**h) for h in data.get("hedge_positions", [])
    ]

    return cw_positions, hedge_positions


# =========================
# SAVE
# =========================

def save_portfolio(cw_positions, hedge_positions):

    data = {
        "cw_positions": [vars(p) for p in cw_positions],
        "hedge_positions": [vars(h) for h in hedge_positions]
    }

    with open(FILE_PATH, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# ADD CW
# =========================

def add_cw(new_pos, cw_positions, hedge_positions):

    cw_positions.append(new_pos)
    save_portfolio(cw_positions, hedge_positions)


# =========================
# REMOVE CW
# =========================

def remove_cw(index, cw_positions, hedge_positions):

    if 0 <= index < len(cw_positions):
        cw_positions.pop(index)
        save_portfolio(cw_positions, hedge_positions)


# =========================
# REMOVE EXPIRED
# =========================

def remove_expired(cw_positions, hedge_positions):

    today = date.today()

    cw_positions = [
        p for p in cw_positions
        if date.fromisoformat(p.expiry) > today
    ]

    save_portfolio(cw_positions, hedge_positions)

    return cw_positions
