"""
evaluate.py
-----------
Offline evaluation script for VERAX's risk engine. Kept separate from
app.py on purpose — this is a tool for measuring model quality, not
something an end user runs.

How it works:
1. Load transactions.json — each one has a ground-truth label
   "is_actually_fraud" (True/False), which we know because WE planted the
   suspicious ones when generating the fake data (in a real system, this
   label would come from confirmed chargebacks/fraud reports).
2. Run every transaction through our rule engine.
3. Treat "MEDIUM or HIGH risk" as "our system says this is fraud".
4. Compare our system's prediction to the ground truth and compute:
     - Precision: of the transactions we flagged, how many were REALLY fraud?
     - Recall: of the transactions that were REALLY fraud, how many did we catch?
     - False positives: legit transactions we wrongly flagged (annoys real customers)
     - False negatives: real fraud we missed (costs the merchant money)
     - False-positive cost: an estimate of the business cost of annoying
       genuine customers with false flags (e.g. friction, support tickets)

Why this matters for the pitch: precision/recall alone can be misleading.
A system that flags EVERYTHING gets perfect recall but terrible precision
(and would annoy every customer). Showing both numbers, plus an honest
cost estimate, is what "the bar" is asking for.
"""

import json
from risk_engine import score_transaction

# Rough estimated cost, in rupees, of ONE false positive: the customer
# support time + friction + possible lost sale from wrongly blocking a
# genuine customer. This is a made-up but realistic-sounding assumption --
# in a real system you'd calibrate this from actual support/ops data.
COST_PER_FALSE_POSITIVE = 150  # INR, illustrative assumption -- state this out loud in your pitch


def build_user_profiles(transactions):
    profiles = {}
    first_seen_device = {}
    for tx in transactions:
        uid = tx["user_id"]
        profiles.setdefault(uid, []).append(tx["amount"])
        first_seen_device.setdefault(uid, tx["device_id"])
    return profiles, first_seen_device


def compute_metrics(transactions=None):
    """
    Reusable evaluation function -- called by both this CLI script AND the
    web app's /analytics page, so the numbers you see in the browser are
    always the same ones this script prints. No duplicated logic.
    """
    if transactions is None:
        with open("transactions.json") as f:
            transactions = json.load(f)

    profiles, first_seen_device = build_user_profiles(transactions)

    tp = fp = tn = fn = 0
    details = []

    for tx in transactions:
        uid = tx["user_id"]
        avg_amount = sum(profiles[uid]) / len(profiles[uid])
        known_devices = [first_seen_device[uid]]
        recent = [t for t in transactions if t["user_id"] == uid]

        result = score_transaction(tx, avg_amount, known_devices, recent)
        predicted_fraud = result["level"] in ("MEDIUM", "HIGH")
        actual_fraud = tx.get("is_actually_fraud", False)

        if predicted_fraud and actual_fraud:
            tp += 1
            outcome = "TRUE POSITIVE (correctly caught fraud)"
        elif predicted_fraud and not actual_fraud:
            fp += 1
            outcome = "FALSE POSITIVE (wrongly flagged a real customer)"
        elif not predicted_fraud and actual_fraud:
            fn += 1
            outcome = "FALSE NEGATIVE (missed real fraud)"
        else:
            tn += 1
            outcome = "TRUE NEGATIVE (correctly left alone)"

        details.append({
            "tx_id": tx["tx_id"], "outcome": outcome,
            "level": result["level"], "reasons": result["reasons"],
        })

    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    fp_cost = fp * COST_PER_FALSE_POSITIVE

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "fp_cost": fp_cost, "cost_per_fp": COST_PER_FALSE_POSITIVE,
        "details": details,
    }


def run_evaluation():
    metrics = compute_metrics()
    tp, fp, tn, fn = metrics["tp"], metrics["fp"], metrics["tn"], metrics["fn"]
    precision, recall, f1 = metrics["precision"], metrics["recall"], metrics["f1"]
    fp_cost = metrics["fp_cost"]
    details = [(d["tx_id"], d["outcome"], d["level"], d["reasons"]) for d in metrics["details"]]

    print("=" * 60)
    print("EVALUATION RESULTS (held-out synthetic test set)")
    print("=" * 60)
    for tx_id, outcome, level, reasons in details:
        print(f"{tx_id:8s} [{level:6s}] {outcome}")
    print("-" * 60)
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"True Negatives:  {tn}")
    print(f"False Negatives: {fn}")
    print("-" * 60)
    print(f"Precision: {precision:.2f}  (of flagged transactions, % that were real fraud)")
    print(f"Recall:    {recall:.2f}  (of real fraud, % that we caught)")
    print(f"F1 Score:  {f1:.2f}")
    print(f"Estimated false-positive cost: ₹{fp_cost} "
          f"(assuming ₹{COST_PER_FALSE_POSITIVE} cost per wrongly-flagged customer)")
    print("=" * 60)


if __name__ == "__main__":
    run_evaluation()
