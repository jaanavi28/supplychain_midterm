# Plan (rev 3, FINAL): BIA674 Midterm, Option B: Agentic Demand Forecasting Advisor

This replaces rev 2 entirely. Build from this file.

**Rev 3.1 (2026-10-31):** aligned with course conventions (course_forecasting_concepts.md): E = F − D, σ = 1.25 × MAD, numpy SES/Holt per Chopra, statsmodels removed, tracking signal outside ±6 added as a review trigger.

**Rev 3.3 (2026-10-31):** SS unchanged under a promo (option a); T2 gets a lead-time variant; T2 names the promo type; vague promo moves to T3; lifts never stacked (largest single type).

**Rev 3.2 (2026-10-31):** promo adjustment = promo_lift output (no fixed cap; > +50% needs planner approval); per-SKU service levels; outputs label holdout fit vs refit; T2 criteria updated.

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
  - (c) Review is triggered whenever MAPE > 30%, |TS| > 6, a policy/memo conflict exists, or a promo adjustment > +50%.
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
- **Error convention (course): E = F − D.** Metrics: MAD, MAPE, bias = ΣE, tracking signal = bias / MAD.
- **σ_error = 1.25 × MAD** of the chosen method's 12 holdout errors (course approximation; replaces std dev).
- Safety stock = z · σ_error · √L (weeks); ROP = forecast over L + SS.
- **SES (numpy loop, Chopra):** L0 = mean of training weeks; α minimizes in-sample MSE over grid 0.01–0.99 (step 0.01).
- **Holt (numpy loop, Chopra):** L0, T0 = intercept and slope of a linear regression of training demand on t; α, β minimize in-sample MSE over the same grid.
- `run_forecasts` outputs L0, T0, α, β, so they can be reproduced in Excel.
- **Two fits:** holdout accuracy and σ come from the fit on weeks 1–118; the forward forecast comes from a refit of the selected method on all 130 weeks. Tool output and agent answers label every number with its fit.
- **promo_lift:** lift % = average units in promo weeks / average units in normal weeks − 1, over all 130 weeks; normal = not featured, not display, discount < 5%; types: featured, display, discount, any.
- Libraries: pandas, numpy (statsmodels removed).
- **Expected holdout MAPE (for sanity check):**

| SKU | Naive | MA(8) | SES | Holt | Selected |
|---|---|---|---|---|---|
| 217390 | 31.42 | 23.89 | 23.79 | 23.93 | SES |
| 219009 | 14.90 | 31.46 | 17.47 | 19.02 | Naive |
| 223245 | 45.88 | 42.04 | 47.05 | 46.64 | MA(8) |

(Rev 3 values for SES/Holt came from statsmodels; naive and MA(8) are unchanged.)

## 4. Agent and tools (7)
Single Claude agent (`claude-haiku-5-5`, ≤8 tool turns, capped max_tokens).

| Tool | Purpose |
|---|---|
| `search_knowledge` | Plain keyword match over doc sections; returns passages with filenames. |
| `get_history` | Weekly sales, price, promo flags, data-quality notes for a SKU. |
| `run_forecasts` | Fits the 4 methods, holdout metrics (holdout fit), fitted parameters, forward forecast (refit), optional adjustment %. |
| `promo_lift` | Historical uplift in featured/display/discount weeks vs normal weeks. |
| `inventory_policy` | SS and ROP from σ_error, lead time, service level. |
| `validate` | Recomputes key numbers; checks the adjustment equals promo_lift (approval flag if > +50%); checks MAPE vs 30% and |TS| vs 6. |
| `request_human_review` | Logs a simulated escalation (no real orders/emails). |

- **Prompt rules:**
  - Every number comes from a tool.
  - Pick the lowest-MAPE method.
  - Promo adjustments equal promo_lift output for the matching type; never stack lifts (largest single type); > +50% needs planner approval.
  - Label each number as holdout fit (weeks 1–118) or refit (weeks 1–130).
  - MAPE differences under 1 point are practical ties: report them.
  - Ask for a missing SKU, or state the policy-default service level.
  - Cite filenames.
  - Flag conflicts and escalate.
  - Out-of-scope requests get a statement of limits plus a simulated escalation.
- `agent/prompts.py` = **v1**. v2 is added only after v1 test review.
- The UI shows the full trace, downloadable as JSON.

## 5. Knowledge base (= context files)
- `data/demand_store8023.csv` (public)
- `docs/forecasting_policy.md` (**synthetic**):
  - Approved methods; lowest holdout MAPE wins; differences < 1 point are practical ties
  - Service levels: default 95%; 217390 = 95%, 219009 = 95%, 223245 = 90%
  - Promo adjustment = promo_lift output (no fixed cap); > +50% requires planner approval
  - **Review triggers: MAPE > 30%, |TS| > 6, policy/memo conflict, adjustment > +50%**
  - Agent never places orders or contacts suppliers
- `docs/sop_memo_v2.md` (**synthetic**, dated 2026-10-28, later than the policy): sets 219009 to 98% for an upcoming promo period; does not say which document governs. For T4.
- `docs/course_forecasting_concepts.md`: own-words summary of Chopra Ch. 7 + instructor slides/Excel (course definitions, formulas, error rules).
- `docs/forecasting_methods.md`: project-specific definitions only (fixed-origin holdout, selection rule, σ, safety stock); refers to the course doc for the rest.
- `inventory.csv`, `data_dictionary.md` (notes no product/store names, weak seasonality).
- Report terminology: KB = context files; validate + v1→v2 = feedback loop; 5 tests = evals.

## 6. Tests / evals (pass criteria in each JSON before running)
- **T1 Typical:** SKU 217390, complete inputs. Pass: picks the lowest-MAPE method, beats naive, matches Excel.
- **T2 Changed** (passes only if both variants pass):
  - **T2a promo:** "SKU 219009 will be featured in the weekly flyer for the next 2 weeks." Pass: adjustment = featured lift +222.0%; forecast and ROP increase; SS unchanged (σ reflects uncertainty, not demand level); planner-approval flag raised (lift > +50%); review flagged for TS (−9.46).
  - **T2b lead time:** SKU 219009, lead time 2 → 4 weeks, no promo. Pass: SS rises by √2 (158.2 → ~223.7 units); ROP rises.
- **T3 Missing:** "There's a promo coming for 219009, what should we stock?" (no promo type, no service level). Pass: uses the "any promo" lift (+136.1%) and states it as an assumption; uses the SKU's policy service level (95%) and states it. (Variant: no SKU → asks for it.)
- **T4 Conflict:** policy vs memo on 219009, and/or a claimed surge the data contradicts. Pass: flags it, cites both, escalates.
- **T5 Unsupported:** PO request / out-of-scope SKU / outside-KB question. Pass: states limits, simulated escalation.
- SKU 223245: MAPE > 30% triggers review. Any selected method with TS outside ±6 also triggers review.
- **Scenario files (criteria written 2026-10-31, before any run):** `tests/scenarios/` T1, T1b (223245 review), T2a, T2b, T3a (vague promo; must ask for lead time; no default lead time), T3b (no SKU), T4a (policy vs memo), T4b (claimed surge vs data), T5a (PO), T5b (out-of-scope SKU), T5c (tariffs). T2: an extra memo-conflict flag counts as correct.
- Policy numbers have one source: `knowledge/policy_values.json` (read by the tools); default horizon 4 weeks; no default lead time.
- Prompt v1 frozen 2026-10-31.
- No test is assumed to fail. After v1, the owner reviews the results, then the improvement is chosen and the affected test rerun as v2.

## 7. Verification
- The owner builds the Excel check (SES with the reported L0 and α, and/or MA(8); MAPE, MAD, σ = 1.25 × MAD, SS for 217390) from `verification/sku217390_series.csv`.
- pytest optional.

## 8. Repo layout
`CLAUDE.md`, `README.md`, `requirements.txt` (streamlit, anthropic, pandas, numpy), `app.py`, `agent/{agent.py, prompts.py, tools.py}`, `analytics/{forecast.py, inventory.py}`, `scripts/prepare_data.py`, `knowledge/…`, `tests/{scenarios/, run_tests.py}`, `evidence/`, `verification/`, `docs/architecture.md` (mermaid).

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
