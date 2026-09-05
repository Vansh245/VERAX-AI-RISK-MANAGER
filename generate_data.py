"""
generate_data.py
-----------------
This script creates synthetic transaction data so there's something to
test the risk engine on. In a production system, this data would come
from actual payments. Here, we hand-craft some "normal" transactions and
seed in a few "suspicious" ones so the app has something interesting to
flag.

This just builds a Python list of dictionaries and saves it as a JSON
file. No AI, no external libraries. Just data.
"""

import json
import random
from datetime import datetime, timedelta

random.seed(42)  # keeps the "random" data the same every time we run this

# A handful of fake users, each with a "normal" spending pattern.
USERS = [
    {"user_id": "U001", "name": "Aarav Shah", "avg_amount": 1200, "known_devices": ["deviceA"]},
    {"user_id": "U002", "name": "Priya Nair", "avg_amount": 800, "known_devices": ["deviceB"]},
    {"user_id": "U003", "name": "Rohan Mehta", "avg_amount": 5000, "known_devices": ["deviceC"]},
    {"user_id": "U004", "name": "Sara Khan", "avg_amount": 300, "known_devices": ["deviceD"]},
]

def random_time(base, hour_range):
    hour = random.choice(hour_range)
    minute = random.randint(0, 59)
    return base.replace(hour=hour, minute=minute)

def build_transactions():
    transactions = []
    tx_id = 1
    base_time = datetime(2026, 9, 1)

    for user in USERS:
        # --- Normal transactions (5 per user) ---
        for _ in range(5):
            amount = round(user["avg_amount"] * random.uniform(0.7, 1.3), 2)
            transactions.append({
                "tx_id": f"TX{tx_id:04d}",
                "user_id": user["user_id"],
                "user_name": user["name"],
                "amount": amount,
                "device_id": user["known_devices"][0],
                "timestamp": random_time(base_time, range(9, 21)).isoformat(),
                "is_actually_fraud": False,  # ground truth label, used only for evaluation
            })
            tx_id += 1

    # --- Suspicious transactions (hand-crafted to trigger our rules) ---

    # 1. Huge amount compared to user's average (TRUE FRAUD - should be caught)
    transactions.append({
        "tx_id": f"TX{tx_id:04d}", "user_id": "U001", "user_name": "Aarav Shah",
        "amount": 45000, "device_id": "deviceA",
        "timestamp": base_time.replace(hour=14, minute=10).isoformat(),
        "is_actually_fraud": True,
    })
    tx_id += 1

    # 2. Unknown device + odd hour (TRUE FRAUD - should be caught)
    transactions.append({
        "tx_id": f"TX{tx_id:04d}", "user_id": "U002", "user_name": "Priya Nair",
        "amount": 950, "device_id": "deviceX-unknown",
        "timestamp": base_time.replace(hour=3, minute=22).isoformat(),
        "is_actually_fraud": True,
    })
    tx_id += 1

    # 3. Round-number amount + unknown device (TRUE FRAUD - should be caught)
    transactions.append({
        "tx_id": f"TX{tx_id:04d}", "user_id": "U003", "user_name": "Rohan Mehta",
        "amount": 50000, "device_id": "deviceZ-unknown",
        "timestamp": base_time.replace(hour=15, minute=0).isoformat(),
        "is_actually_fraud": True,
    })
    tx_id += 1

    # 4. Velocity burst: 4 transactions within 10 minutes (TRUE FRAUD - should be caught)
    burst_start = base_time.replace(hour=18, minute=0)
    for i in range(4):
        transactions.append({
            "tx_id": f"TX{tx_id:04d}", "user_id": "U004", "user_name": "Sara Khan",
            "amount": 300 + i * 20, "device_id": "deviceD",
            "timestamp": (burst_start + timedelta(minutes=i * 2)).isoformat(),
            "is_actually_fraud": True,
        })
        tx_id += 1

    # 5. HARD NEGATIVE: legit but unusual - user genuinely spending more than
    #    usual (e.g. a real big purchase) on their KNOWN device, normal hour.
    #    Our rules may still flag this on amount alone -> honest false positive.
    transactions.append({
        "tx_id": f"TX{tx_id:04d}", "user_id": "U003", "user_name": "Rohan Mehta",
        "amount": 42000, "device_id": "deviceC",  # known device, not round number
        "timestamp": base_time.replace(hour=13, minute=0).isoformat(),
        "is_actually_fraud": False,
    })
    tx_id += 1

    # 6. HARD POSITIVE (sneaky fraud): small amount, known device, normal hour,
    #    but actually fraudulent (e.g. a stolen-card tester making a tiny
    #    purchase to test if the card works). Our current rules will likely
    #    MISS this -> an honest false negative, worth discussing in your pitch.
    transactions.append({
        "tx_id": f"TX{tx_id:04d}", "user_id": "U002", "user_name": "Priya Nair",
        "amount": 50, "device_id": "deviceB",
        "timestamp": base_time.replace(hour=11, minute=15).isoformat(),
        "is_actually_fraud": True,
    })
    tx_id += 1

    return transactions

if __name__ == "__main__":
    data = build_transactions()
    with open("transactions.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} transactions -> transactions.json")
