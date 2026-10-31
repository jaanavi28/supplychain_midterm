# BIA674 Midterm — Agentic Demand Forecasting Advisor

## Context
- Final plan: docs/plan.md (rev 3). Build from it.
- Graded class project. Rubric rewards clarity, not complexity.
- Owner is not a developer: explain changes in plain language, one line per file changed.

## Rules
- Simplest code that works. No new libraries/tools without asking.
- Every number the agent outputs must come from a tool. No hardcoded results.
- Never commit API keys. Key is user-pasted at runtime only.
- Don't edit raw data in knowledge/data/. Preparation happens in scripts/prepare_data.py.
- Don't change prompts.py v1 after tests are run — create v2 instead (before/after evidence).
- Don't fabricate test results or traces. Tests must actually run.

## Scope
- Store 8023, SKUs 217390 (stable, T1), 219009 (promo-driven, T2/T4), 223245 (volatile, MAPE-triggered review). Weekly buckets.
- Data: train.csv only (in knowledge/data/raw/). No test.csv; T2 promo is typed by the user.
- Holdout: fixed-origin. Train on weeks 1–118, forecast weeks 119–130 in one shot (12 weeks).
- Methods: naive (last training value ×12), MA(8) (mean of last 8 training weeks, repeated), SES, Holt (statsmodels).
- run_forecasts reports fitted SES alpha, Holt alpha/beta, and initial level (for Excel reproduction).
- Selection rule: lowest holdout MAPE wins (naive may win).
- σ_error for safety stock = std dev of the chosen method's 12 holdout errors.
- Policy: MAPE review threshold = 30%.
- Libraries: statsmodels yes; scikit-learn no (search_knowledge uses plain keyword matching).
- Verification export: verification/sku217390_series.csv.

## Done =
- App runs locally and on Streamlit, 5 tests produce evidence JSON, README lets the instructor reproduce a run.
- Success: (a) lowest-MAPE method selected per SKU, 217390 beats naive; (b) 100% of output numbers match tool output and the Excel check; (c) review triggered whenever MAPE > 30% or a policy/memo conflict exists.
