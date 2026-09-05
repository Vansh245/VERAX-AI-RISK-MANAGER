# VERAX

A rule-based fraud and risk detection engine for payment transactions, with
plain-English explanations for every flag.

## The problem

Merchants lose money to fraud, and support teams lose time reviewing
flagged transactions with no context on *why* something looks suspicious.
VERAX detects suspicious payment activity and explains each flag in plain
language, so a human reviewer can act quickly and with confidence.

## How it works

```
transactions.json (data)
        │
        ▼
risk_engine.py  ──►  Five explainable rules score each transaction
        │             (amount spike, velocity, unknown device,
        │              odd hour, round-number amount)
        ▼
ai_explainer.py ──►  Turns the triggered rules into a plain-English
        │             explanation for a human reviewer (falls back to a
        │             template if no API key is set — still fully functional)
        ▼
app.py (Flask)  ──►  Dashboard UI: lists transactions by risk level,
                      click through for the full explanation

evaluate.py     ──►  Offline script that measures precision, recall, and
                      false-positive cost against labeled ground truth
```

**Design choice — rules, not a black-box model, decide the risk score.**
The AI layer is used only to explain a decision that transparent logic has
already made. In fraud and risk, explainability matters as much as
accuracy — a reviewer, or a customer disputing a block, needs a real
reason, not "the model said so." VERAX never blocks a transaction
automatically; a human reviewer always makes the final call.

## Results

Run `python evaluate.py` to reproduce:

| Metric | Value |
|---|---|
| Precision | 1.00 |
| Recall | 0.88 |
| F1 | 0.93 |
| False positives | 0 |
| False negatives | 1 |
| Est. false-positive cost | ₹0 (0 × ₹150/incident, illustrative) |

The test set includes two deliberately hard cases:
- A **legitimate but unusually large purchase** on a known device — correctly
  left alone, no false alarm.
- A **small ₹50 "card-testing" style fraud** on a known device at a normal
  hour — missed. This is an honest limitation: the current rules key off
  amount, velocity, device, and time, and a small test charge looks like
  normal behavior on all four. A production version would add a "new
  payee/merchant for this card" signal to catch this pattern.

## Getting started

```bash
pip install -r requirements.txt
python generate_data.py     # creates the synthetic transaction dataset
python evaluate.py          # prints precision/recall/cost metrics
python app.py                # starts the dashboard at localhost:5000
```

Optional: set `ANTHROPIC_API_KEY` as an environment variable to get
live LLM-generated explanations instead of the template fallback.

## Scope

- Detection and explanation only — no automated blocking or retaliatory
  action.
- No live "test any input" tool. An earlier version of this project let a
  signed-in user submit an arbitrary hypothetical transaction and see the
  exact rule breakdown. That's useful for a demo, but it also hands anyone
  with a login a way to probe the precise thresholds that do and don't
  trigger a flag — which is the same technique used to evade a real fraud
  system. It was removed to keep this strictly defense-only: the system
  scores transactions that actually happened, not hypothetical ones
  supplied to find the edge of detection.
- Uses synthetic data, not production transactions.
- Five rules were chosen for clarity and explainability; a production
  system would tune weights against real historical fraud data instead
  of hand-picked thresholds.

## Tech stack

Python, Flask, vanilla HTML/CSS, Anthropic API (optional). No ML
libraries used, by design — see "Design choice" above.
