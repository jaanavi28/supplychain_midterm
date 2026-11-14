# BIA674 Midterm: Agentic Demand Forecasting Advisor

An AI agent that acts as a senior supply chain analyst for the demand planner at store 8023 of a
76-store retail chain. For three SKUs (217390, 219009, 223245) it compares forecasting methods on a
12-week holdout, picks the most accurate one, applies measured promotion lifts, sets safety stock
and reorder points, checks its own numbers, and escalates to a human when the policy requires it.

- Course topic: Demand Forecasting (Chopra et al., Ch. 7), linked to inventory and S&OP.
- Option B (agentic prototype): one Claude agent (`claude-haiku-5-5`) with 7 tools.
- Data: public Kaggle / Analytics Vidhya retail demand dataset (train.csv), weekly, Jan 2011 to Jul 2013.
  The policy and S&OP memo are **synthetic** and labelled as such.
- Full plan: `docs/plan.md`.

## How it works

1. The planner describes the SKU, lead time, service level and current conditions.
2. The agent (instructions in `agent/prompts.py`) calls tools (`agent/tools.py`):
   `search_knowledge`, `get_history`, `run_forecasts`, `promo_lift`, `inventory_policy`,
   `validate`, `request_human_review`.
3. All numbers come from the tools (`analytics/`), never from the model.
4. `validate` recomputes the numbers and applies the review triggers
   (MAPE > 30%, |TS| > 6, policy/memo conflict, promo adjustment > +50%).
5. Escalations and orders are **simulated**; nothing is sent anywhere.

## Repository layout

| Path | What it is |
|---|---|
| `app.py` | Streamlit app: Advisor (chat) tab and Test runner tab |
| `agent/` | Agent loop, prompt versions, tool definitions |
| `analytics/` | Forecasting (naive, MA(8), SES, Holt), inventory, promo lift |
| `knowledge/` | Knowledge base: data, docs, `policy_values.json`, `inventory.csv`, `data_dictionary.md` |
| `scripts/prepare_data.py` | Builds the prepared dataset from the raw file |
| `tests/scenarios/` | Test scenarios with pass criteria written before running |
| `tests/run_tests.py` | Command-line test runner (same evidence format as the app) |
| `verification/` | Series export for the independent Excel check |
| `evidence/` | Saved test evidence (added after the runs) |

## Requirements

- **Python 3.13** (tested on 3.13).
- Packages in `requirements.txt`: streamlit, anthropic, pandas, numpy.
- An Anthropic API key. It is typed into the app at runtime, kept only in the browser session,
  and never stored in this repository.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Paste your API key in the sidebar. Use the **Advisor** tab to ask questions, or the
**Test runner** tab to run the scenarios and download the evidence as a zip.

Command-line alternative for the tests (asks for the key with hidden input; never overwrites
existing evidence):

```bash
python tests/run_tests.py
```

To rebuild the prepared data from the raw file:

```bash
python scripts/prepare_data.py
```

## Deploy on Streamlit Community Cloud

1. Sign in at share.streamlit.io with the GitHub account that can see this repository.
2. Create app: repository `jaanavi28/supplychain_midterm`, branch `claude/elegant-fermat-huqak3`,
   main file `app.py`.
3. Advanced settings: Python version **3.13**. No secrets are needed.
4. Deploy, then share the app with the instructor by email (app settings, Sharing).

## Reproducing a run without the live app

The saved traces in `evidence/` show each tool call and result. The knowledge base files and
`tests/scenarios/` contain everything needed to rerun the same scenarios locally.
