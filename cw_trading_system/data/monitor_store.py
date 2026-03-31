# data/monitor_store.py

import json
from datetime import datetime

FILE_PATH = "data/monitor_log.json"


def load_logs():
    try:
        with open(FILE_PATH, "r") as f:
            return json.load(f)
    except:
        return []


def save_logs(logs):
    with open(FILE_PATH, "w") as f:
        json.dump(logs, f, indent=4)


def record_snapshot(risk, pnl):

    logs = load_logs()

    logs.append({
        "time": datetime.now().isoformat(),
        "delta": risk["total"]["delta"],
        "gamma": risk["total"]["gamma"],
        "vega": risk["total"]["vega"],
        "theta": risk["total"]["theta"],
        "pnl": pnl["total_pnl"]
    })

    save_logs(logs)
