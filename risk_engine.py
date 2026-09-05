"""
risk_engine.py
--------------
Core scoring logic for VERAX. Intentionally rule-based rather than a
machine-learning model: in fraud/risk systems, being able to explain
exactly why a transaction was flagged is often more valuable than a
marginal gain in accuracy from a black-box model.

Each rule checks one thing about a transaction and adds "risk points" if it
looks suspicious. Points are summed to a final score:
    0-1 points  -> LOW risk
    2-3 points  -> MEDIUM risk
    4+ points   -> HIGH risk

The function returns not just the score, but WHICH rules fired -- this list
is what we later hand to the AI so it can explain the decision in plain
English.
"""

from datetime import datetime

# How much each triggered rule adds to the risk score.
RULE_WEIGHTS = {
    "high_amount": 2,
    "velocity": 2,
    "unknown_device": 1,
    "odd_hour": 1,
    "round_number": 1,
}


def check_high_amount(transaction, user_avg_amount):
    """Rule 1: Is this transaction much bigger than the user's usual amount?"""
    if transaction["amount"] > 3 * user_avg_amount:
        return True, f"Amount (₹{transaction['amount']}) is more than 3x this user's average (₹{user_avg_amount})"
    return False, None


def check_velocity(transaction, user_recent_transactions, window_minutes=10, max_count=3):
    """Rule 2: Has this user made too many transactions in a short window?"""
    tx_time = datetime.fromisoformat(transaction["timestamp"])
    count = 0
    for other in user_recent_transactions:
        if other["tx_id"] == transaction["tx_id"]:
            continue
        other_time = datetime.fromisoformat(other["timestamp"])
        if abs((tx_time - other_time).total_seconds()) <= window_minutes * 60:
            count += 1
    if count >= max_count:
        return True, f"{count} other transactions from this user within {window_minutes} minutes"
    return False, None


def check_unknown_device(transaction, known_devices):
    """Rule 3: Is this device one we've never seen for this user?"""
    if transaction["device_id"] not in known_devices:
        return True, f"Device '{transaction['device_id']}' has not been seen before for this user"
    return False, None


def check_odd_hour(transaction, odd_hour_range=(0, 5)):
    """Rule 4: Did this happen at an unusual hour (e.g. 12am-5am)?"""
    hour = datetime.fromisoformat(transaction["timestamp"]).hour
    if odd_hour_range[0] <= hour <= odd_hour_range[1]:
        return True, f"Transaction occurred at {hour}:00, an unusual hour"
    return False, None


def check_round_number(transaction, threshold=10000):
    """Rule 5: Is the amount a suspiciously round number above a threshold?"""
    amount = transaction["amount"]
    if amount >= threshold and amount % 1000 == 0:
        return True, f"Amount (₹{amount}) is a suspiciously round number"
    return False, None


def score_transaction(transaction, user_avg_amount, known_devices, user_recent_transactions):
    """
    Runs every rule against one transaction and returns:
      - total risk score (number)
      - risk level ("LOW", "MEDIUM", "HIGH")
      - a list of human-readable reasons for every rule that fired
    """
    triggered_reasons = []
    score = 0

    fired, reason = check_high_amount(transaction, user_avg_amount)
    if fired:
        score += RULE_WEIGHTS["high_amount"]
        triggered_reasons.append(reason)

    fired, reason = check_velocity(transaction, user_recent_transactions)
    if fired:
        score += RULE_WEIGHTS["velocity"]
        triggered_reasons.append(reason)

    fired, reason = check_unknown_device(transaction, known_devices)
    if fired:
        score += RULE_WEIGHTS["unknown_device"]
        triggered_reasons.append(reason)

    fired, reason = check_odd_hour(transaction)
    if fired:
        score += RULE_WEIGHTS["odd_hour"]
        triggered_reasons.append(reason)

    fired, reason = check_round_number(transaction)
    if fired:
        score += RULE_WEIGHTS["round_number"]
        triggered_reasons.append(reason)

    if score >= 4:
        level = "HIGH"
    elif score >= 2:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {"score": score, "level": level, "reasons": triggered_reasons}
