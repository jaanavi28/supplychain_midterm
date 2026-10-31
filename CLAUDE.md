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
- Methods: naive (last training value ×12), MA(8) (mean of last 8 training weeks, repeated), SES, Holt — plain numpy loops per Chopra Ch. 7 (SES L0 = training mean; Holt L0/T0 from regression on t; α, β by min in-sample MSE over grid 0.01–0.99).
- run_forecasts reports L0, T0, α, β (for Excel reproduction).
- Course conventions (knowledge/docs/course_forecasting_concepts.md): E = F − D, bias = ΣE, TS = bias / MAD.
- Selection rule: lowest holdout MAPE wins (naive may win).
- σ for safety stock = 1.25 × MAD of the chosen method's 12 holdout errors.
- Policy review triggers: MAPE > 30%, |TS| > 6, policy/memo conflict, promo adjustment > +50% (needs planner approval).
- Promo adjustment = promo_lift output for the matching type (no fixed cap); never stack lifts — use the largest single-type lift. SS does not change with a promo.
- Holdout accuracy and σ come from the fit on weeks 1–118; forward forecast from a refit on weeks 1–130. Label which fit each number comes from.
- Libraries: streamlit, anthropic, pandas, numpy only (no statsmodels, no scikit-learn; search_knowledge uses plain keyword matching).
- Verification export: verification/sku217390_series.csv.

## Done =
- App runs locally and on Streamlit, 5 tests produce evidence JSON, README lets the instructor reproduce a run.
- Success: (a) lowest-MAPE method selected per SKU, 217390 beats naive; (b) 100% of output numbers match tool output and the Excel check; (c) review triggered whenever MAPE > 30%, |TS| > 6, a policy/memo conflict, or adjustment > +50%.
