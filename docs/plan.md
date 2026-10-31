# Plan (rev 3, FINAL): BIA674 Midterm, Option B: Agentic Demand Forecasting Advisor

This replaces rev 2 entirely. Build from this file.

## Context
BIA674 Individual Midterm, Option B: an agentic prototype that sequences actions, uses analytical/retrieval tools, checks its results and recommends a decision. Topic: **Demand Forecasting (Module 5)**, linked to inventory/S&OP. The agent acts as a **senior supply chain analyst (~20 yrs)**. It runs on **Streamlit Community Cloud (free, private app)** with **Anthropic Claude**, and the **API key is pasted at runtime**. Minimum code. Repo `jaanavi28/supplychain_midterm`, branch `claude/elegant-fermat-huqak3`.

## Step 0: `CLAUDE.md` at repo root (first commit)
As specified earlier, with **Scope = Store 8023; SKUs 217390, 219009, 223245; weekly; 12-week fixed-origin holdout; naive, MA(8), SES, Holt.**

## 1. Problem definition (report section)
- **Setting:** a retail chain with 76 stores; the demand planner at store 8023.
- **Current process:** manual spreadsheet forecasting, eyeballing recent weeks, gut-feel promo bumps, no error tracking or safety-stock logic.
- **Decision:** for one SKU, choose the forecast for the next N weeks, set safety stock and reorder point, and decide whether to escalate to S&OP / human review.
- **Inputs:** SKU, horizon (weeks), lead time (weeks), service level, context (planned promo, claimed trend).
- **Outputs:** chosen method plus holdout accuracy vs naive, forecast table, promo adjustment with its source, SS/ROP, actions, cited sources, assumptions, approvals needed.
- **Success criterion:**
  - (a) The agent selects the lowest holdout-MAPE method for each SKU; for 217390 that method beats naive.
  - (b) 100% of numbers in outputs match tool output and the independent Excel check.
  - (c) Review is triggered whenever MAPE > 30% or a policy/memo conflict exists.
- **Why agentic vs GPT:** the decision needs real calculations plus a validation step; the agent computes with tools, checks the results, and escalates by rule.
- **Course concepts:** level/trend, MA, exponential smoothing, Holt, MAE/MAPE/bias/tracking signal, judgmental (promo) adjustment, safety stock, S&OP escalation.

## 2. Dataset
- Kaggle / Analytics Vidhya retail demand forecasting dataset: 76 stores, weekly SKU-store sales, Jan 2011 to Jul 2013. **Public**, labeled.
- **train.csv only.** test.csv and sample_submission.csv are **not used** (no actuals).
- Columns: `record_ID, week (dd/mm/yy, explicit format), store_id, sku_id, total_price, base_price, is_featured_sku, is_display_sku, units_sold`.
- `scripts/prepare_data.py`:
  - Parse dates; filter store 8023 and the 3 SKUs.
  - Fill the 1 missing `total_price` with `base_price` (logged).
  - Derive `discount = (base_price − total_price) / base_price`.
  - Write `knowledge/data/demand_store8023.csv`. Raw files in `knowledge/data/raw/` are never edited.
  - Export `verification/sku217390_series.csv` for the Excel check.
- **SKU roles:**
  - 217390 stable (T1)
  - 219009 promo-driven (T2/T4)
  - 223245 volatile (MAPE-triggered review)

## 3. Methods
- Naive (baseline), MA(8), SES, Holt (trend, no seasonality). Holt-Winters dropped: 2.5 years is too few seasons.
- **Holdout: fixed-origin.**
  - Train on weeks 1–118; forecast weeks 119–130 in one shot.
  - Naive = last training value × 12.
  - MA(8) = mean of the last 8 training weeks × 12.
- **Method selection:** lowest holdout MAPE wins (naive may win).
- Metrics: MAE, MAPE, bias, tracking signal = Σerror / MAD.
- **σ_error** = std dev of the chosen method's 12 holdout errors.
- Safety stock = z · σ_error · √L (weeks); ROP = forecast over L + SS.
- `run_forecasts` outputs fitted SES alpha, Holt alpha/beta and initial level, so they can be reproduced in Excel.
- Libraries: pandas, numpy, statsmodels.
- **Expected holdout MAPE (for sanity check):**

| SKU | Naive | MA(8) | SES | Holt |
|---|---|---|---|---|
| 217390 | 31.4 | 23.9 | 23.9 | 23.9 |
| 219009 | 14.9 | 31.5 | 16.7 | 21.1 |
| 223245 | 45.9 | 42.0 | 34.9 | 35.9 |

## 4. Agent and tools (7)
Single Claude agent (`claude-haiku-5-5`, ≤8 tool turns, capped max_tokens).

| Tool | Purpose |
|---|---|
| `search_knowledge` | Plain keyword match over doc sections; returns passages with filenames. |
| `get_history` | Weekly sales, price, promo flags, data-quality notes for a SKU. |
| `run_forecasts` | Fits the 4 methods, holdout metrics, fitted parameters, optional adjustment %. |
| `promo_lift` | Historical uplift in featured/display/discount weeks vs normal weeks. |
| `inventory_policy` | SS and ROP from σ_error, lead time, service level. |
| `validate` | Recomputes key numbers; checks the adjustment is within the cap and backed by promo_lift; checks MAPE vs the 30% threshold. |
| `request_human_review` | Logs a simulated escalation (no real orders/emails). |

- **Prompt rules:**
  - Every number comes from a tool.
  - Pick the lowest-MAPE method.
  - Promo adjustments use promo_lift output, capped by policy.
  - Ask for a missing SKU, or state the policy-default service level.
  - Cite filenames.
  - Flag conflicts and escalate.
  - Out-of-scope requests get a statement of limits plus a simulated escalation.
- `agent/prompts.py` = **v1**. v2 is added only after v1 test review.
- The UI shows the full trace, downloadable as JSON.

## 5. Knowledge base (= context files)
- `data/demand_store8023.csv` (public)
- `docs/forecasting_policy.md` (**synthetic**):
  - Approved methods and the lowest-MAPE selection rule
  - Service levels per SKU (219009 = 95%) and a default
  - Adjustment cap
  - **MAPE review threshold = 30%**
- `docs/sop_memo_v2.md` (**synthetic**): conflicts with the policy (219009 = 98%), for T4.
- `docs/forecasting_methods.md`: formulas, metrics, holdout and σ definitions.
- `inventory.csv`, `data_dictionary.md` (notes no product/store names, weak seasonality).
- Report terminology: KB = context files; validate + v1→v2 = feedback loop; 5 tests = evals.

## 6. Tests / evals (pass criteria in each JSON before running)
- **T1 Typical:** SKU 217390, complete inputs. Pass: picks the lowest-MAPE method, beats naive, matches Excel.
- **T2 Changed:** SKU 219009 + a user-typed promo. Pass: forecast/SS/ROP move the correct direction; the adjustment comes from promo_lift and stays within the cap.
- **T3 Missing:** no service level and/or no SKU. Pass: asks, or states the policy default.
- **T4 Conflict:** policy vs memo on 219009, and/or a claimed surge the data contradicts. Pass: flags it, cites both, escalates.
- **T5 Unsupported:** PO request / out-of-scope SKU / outside-KB question. Pass: states limits, simulated escalation.
- SKU 223245: MAPE > 30% triggers review.
- No test is assumed to fail. After v1, the owner reviews the results, then the improvement is chosen and the affected test rerun as v2.

## 7. Verification
- The owner builds the Excel check (MA(8) and/or SES with the reported alpha, MAPE, SS for 217390) from `verification/sku217390_series.csv`.
- pytest optional.

## 8. Repo layout
`CLAUDE.md`, `README.md`, `requirements.txt` (streamlit, anthropic, pandas, numpy, statsmodels), `app.py`, `agent/{agent.py, prompts.py, tools.py}`, `analytics/{forecast.py, inventory.py}`, `scripts/prepare_data.py`, `knowledge/…`, `tests/{scenarios/, run_tests.py}`, `evidence/`, `verification/`, `docs/architecture.md` (mermaid).

## 9. Deployment and access
- Private GitHub repo + private Streamlit app; instructor access via email invite.
- API key in a password field, session state only, never committed.
- Reproducible without the live app: README + saved traces + KB files.

## 10. Deliverables (prefix `BIA674_Midterm_Vemana`)
- [ ] Report, 4–6 pages, incl. AI disclosure
- [ ] Video, 10–15 min
- [ ] Prototype package
- [ ] Evidence appendix (T1–T5 traces, Excel check, before/after)

## Build order
1. CLAUDE.md
2. Owner uploads **train.csv** to `knowledge/data/raw/`
3. prepare_data + series export
4. Analytics — **check holdout MAPEs match the table in section 3**
5. KB docs
6. Tools + agent + prompt v1
7. app.py
8. Scenario JSONs
9. Run v1 tests
10. Owner review → v2
11. Deploy

Explain each step in plain language, one line per file.
