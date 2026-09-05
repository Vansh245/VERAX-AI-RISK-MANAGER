"""
app.py
------
The web server. Pages:

  /login        Demo sign-in (any email/password works - see login.html note)
  /             Overview  - summary stats + top flagged transactions + nav cards
  /transactions Full transaction list, filterable
  /analytics    Precision/recall/F1 measured against labeled ground truth

A simple Flask session cookie gates access: visiting any page without
being "signed in" redirects to /login first. This is a demo auth flow
(no password hashing or user database) - intentionally scoped down for
a prototype, and clearly labeled as such on the login page.
"""

from flask import Flask, render_template, request, redirect, session
import json
import os

from risk_engine import score_transaction
from ai_explainer import explain_transaction
from evaluate import compute_metrics

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-secret-change-me")

# ---- Load data once when the server starts ----
with open("transactions.json") as f:
    ALL_TRANSACTIONS = json.load(f)

USER_PROFILES = {}
for tx in ALL_TRANSACTIONS:
    uid = tx["user_id"]
    if uid not in USER_PROFILES:
        USER_PROFILES[uid] = {"amounts": [], "name": tx["user_name"]}
    USER_PROFILES[uid]["amounts"].append(tx["amount"])

first_seen_device = {}
for tx in ALL_TRANSACTIONS:
    first_seen_device.setdefault(tx["user_id"], tx["device_id"])


def get_user_avg(user_id):
    amounts = USER_PROFILES[user_id]["amounts"]
    return sum(amounts) / len(amounts)


def score_all_transactions():
    scored = []
    for tx in ALL_TRANSACTIONS:
        user_id = tx["user_id"]
        avg_amount = get_user_avg(user_id)
        known_devices = [first_seen_device[user_id]]
        recent = [t for t in ALL_TRANSACTIONS if t["user_id"] == user_id]
        result = score_transaction(tx, avg_amount, known_devices, recent)
        scored.append({**tx, "risk": result})
    return scored


def require_login():
    """Returns a redirect response if not signed in, else None."""
    if "user" not in session:
        return redirect("/login")
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        session["user"] = email or "demo@verax.app"
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


@app.route("/")
def landing():
    if "user" in session:
        return redirect("/dashboard")
    return render_template("landing.html")


@app.route("/dashboard")
def home():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    scored_transactions = score_all_transactions()
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    scored_transactions.sort(key=lambda t: order[t["risk"]["level"]])

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for t in scored_transactions:
        counts[t["risk"]["level"]] += 1

    top_risk = [t for t in scored_transactions if t["risk"]["level"] != "LOW"][:5]
    metrics = compute_metrics(ALL_TRANSACTIONS)

    return render_template("dashboard.html", counts=counts, top_risk=top_risk,
                            metrics=metrics, active="dashboard",
                            session_user=session.get("user"))


@app.route("/transactions")
def transactions():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    scored_transactions = score_all_transactions()
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    scored_transactions.sort(key=lambda t: order[t["risk"]["level"]])

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for t in scored_transactions:
        counts[t["risk"]["level"]] += 1

    return render_template("transactions.html", transactions=scored_transactions,
                            counts=counts, active="transactions",
                            session_user=session.get("user"))


@app.route("/transaction/<tx_id>")
def transaction_detail(tx_id):
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    scored_transactions = score_all_transactions()
    tx = next(t for t in scored_transactions if t["tx_id"] == tx_id)
    explanation = explain_transaction(tx, tx["risk"])
    return render_template("detail.html", tx=tx, explanation=explanation,
                            active="transactions", session_user=session.get("user"))


@app.route("/analytics")
def analytics():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    metrics = compute_metrics(ALL_TRANSACTIONS)
    return render_template("analytics.html", metrics=metrics, active="analytics",
                            session_user=session.get("user"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
