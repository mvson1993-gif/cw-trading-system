# data/trade_store.py

import json
from datetime import datetime

FILE_PATH = "data/trades.json"


def load_trades():
    try:
        with open(FILE_PATH, "r") as f:
            return json.load(f)
    except:
        return []


def save_trades(trades):
    with open(FILE_PATH, "w") as f:
        json.dump(trades, f, indent=4)


def record_trade(underlying, action, size, price):

    trades = load_trades()

    trades.append({
        "time": datetime.now().isoformat(),
        "underlying": underlying,
        "action": action,
        "size": size,
        "price": price
    })

    save_trades(trades)
