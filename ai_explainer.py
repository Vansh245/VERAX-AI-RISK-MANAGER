"""
ai_explainer.py
---------------
This is the ONLY file that talks to an AI model. Its job is narrow on
purpose: given a transaction and the list of rules that fired, ask the LLM
to write a short, human-readable explanation for a fraud reviewer.

The AI does NOT decide the risk score. It does NOT decide whether to block
the transaction. It only explains what the rule engine already decided.
This separation is important to be able to explain in your interview:
"The AI never makes the risk decision -- it only translates the decision
into plain language for a human."

If no API key is set, this file falls back to a simple template-based
explanation so the app still works end-to-end without spending any money.
"""

import os
import json
import urllib.request

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _fallback_explanation(transaction, risk_result):
    """No API key? Build a simple explanation without calling any AI."""
    reasons_text = "; ".join(risk_result["reasons"])
    return (
        f"This transaction was flagged as {risk_result['level']} risk "
        f"(score {risk_result['score']}). Reasons: {reasons_text}."
    )


def explain_transaction(transaction, risk_result):
    """
    Calls the Anthropic API to turn rule-based signals into a plain-English
    explanation. Falls back to a template if no API key is configured.
    """
    if not risk_result["reasons"]:
        return "No risk signals were triggered for this transaction."

    if not ANTHROPIC_API_KEY:
        return _fallback_explanation(transaction, risk_result)

    prompt = f"""You are helping a fraud/risk reviewer at a payments company.
A transaction was flagged by a rule-based system with the following details:

Transaction: ₹{transaction['amount']} by user {transaction['user_name']} on device {transaction['device_id']} at {transaction['timestamp']}
Risk level: {risk_result['level']} (score: {risk_result['score']})
Triggered rules: {json.dumps(risk_result['reasons'])}

Write a 2-3 sentence plain-English explanation for the reviewer, explaining
why this transaction looks risky and what they should check next. Be direct
and factual, do not exaggerate."""

    body = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except Exception as e:
        # If the API call fails for any reason, don't crash the app --
        # just fall back to the template explanation.
        return _fallback_explanation(transaction, risk_result) + f" (AI explanation unavailable: {e})"
