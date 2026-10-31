---
title: Course Forecasting Concepts (BIA674, Module 5)
source: Summarized in own words from Chopra, Meindl & Kalra, "Supply Chain Management: Strategy, Planning, and Operation", Ch. 7 "Demand Forecasting in a Supply Chain"; instructor's Ch. 7 slides and Excel workbooks (Tahoe Salt, Examples 7-1 to 7-4, SPC case).
version: v1, 2026-10-30
type: explanatory summary (not a copy of course material)
purpose: Gives the agent the course's definitions, formulas and decision rules so its method choice, error metrics and recommendations follow course conventions.
---

# Course Forecasting Concepts

## 1. Why forecasting matters
- All supply chain decisions made before demand is known are made to a forecast: inventory, ordering, production, promotions, capacity.
- **Push processes** (e.g., store replenishment) need a forecast of demand. **Pull processes** need a forecast to size capacity and inventory.
- Each stage forecasting alone creates mismatches. **Collaborative forecasting** (shared across functions/partners) is more accurate.
- Promotions must be shared: if a retailer plans a promo but the supplier forecasts from history, supply will not match demand.

## 2. Four characteristics of forecasts
1. **Forecasts are always wrong.** Report the expected value AND a measure of forecast error.
2. **Long-term forecasts are less accurate** than short-term (larger error relative to the mean).
3. **Aggregate forecasts are more accurate** than disaggregate (SKU-store is the hardest level).
4. **The further upstream, the more distortion** (bullwhip effect).

## 3. Factors that influence demand
- Past demand
- Replenishment lead time
- Planned advertising / marketing
- **Planned price discounts and promotions**
- State of the economy
- Competitor actions

## 4. Types of forecasting methods
| Type | Basis | Best when |
|---|---|---|
| Qualitative | Human judgment | Little data, or experts have market intelligence |
| Time series | Historical demand only | Demand pattern is stable over time |
| Causal | Demand linked to other factors (price, promos, economy) | Measuring the effect of a promotion or price change |
| Simulation | Imitates consumer choices | What-if questions (promo, competitor entry) |
- Combining several methods often beats any single method.
- **Human judgment stays in the loop:** the system recommends; the manager makes the final call using information not in the data (e.g., weather, local events).

## 5. Components of demand
- **Observed demand = systematic component + random component.**
- Systematic component: **level** (current deseasonalized demand), **trend** (growth/decline per period), **seasonality** (predictable fluctuation).
- Random component: cannot be forecast in direction; only its size/variability can be estimated. That estimate is the forecast error.
- Goal of forecasting: capture the systematic part and filter out the noise.
- Warning sign: a method with near-zero error on history is overfitting (it has absorbed noise) and will forecast poorly.
- Forms of the systematic component: multiplicative (L × T × S), additive (L + T + S), mixed ((L + T) × S).

## 6. Five-step basic approach
1. Understand the objective (which decision does the forecast support?).
2. Integrate forecasting with planning across the supply chain.
3. Identify the major factors influencing demand.
4. Forecast at the right level of aggregation.
5. Set performance and error measures for the forecast.

## 7. Static vs adaptive methods
- **Static:** level, trend and seasonality estimated once (e.g., regression) and not updated.
- **Adaptive:** estimates are updated after each new demand observation.
- Adaptive steps: **initialize → forecast → compute error → update estimates → repeat.**

## 8. Method selection by demand pattern
| Demand pattern | Course method |
|---|---|
| No trend, no seasonality | Moving average or simple exponential smoothing |
| Trend, no seasonality | Holt's model (trend-corrected exponential smoothing) |
| Trend and seasonality | Winter's model (trend- and seasonality-corrected) |
- Pick the method with the lowest error on the chosen error measure.

## 9. Formulas (course notation)
Notation: D_t = actual demand in period t; F_t = forecast for period t; L_t = level; T_t = trend; S_t = seasonal factor.

### Moving average (N periods)
- L_t = (D_t + D_(t−1) + … + D_(t−N+1)) / N
- F_(t+1) = L_t, and F_(t+n) = L_t (flat forecast for all future periods)

### Simple exponential smoothing (SES)
- Initial level: **L_0 = average of all historical demand used for fitting**
- L_(t+1) = α·D_(t+1) + (1 − α)·L_t, with 0 < α < 1
- F_(t+1) = L_t, and F_(t+n) = L_t

### Holt's model (level + trend)
- Initialize: regress demand on time, D_t = a·t + b → **T_0 = a (slope), L_0 = b (intercept)**
- L_(t+1) = α·D_(t+1) + (1 − α)·(L_t + T_t)
- T_(t+1) = β·(L_(t+1) − L_t) + (1 − β)·T_t
- F_(t+1) = L_t + T_t; F_(t+n) = L_t + n·T_t

### Winter's model (level + trend + seasonality)
- F_(t+1) = (L_t + T_t)·S_(t+1)
- Level, trend and seasonal factors each have a smoothing constant (α, β, γ).
- Needs multiple full seasonal cycles to estimate seasonal factors reliably.

## 10. Measures of forecast error
- **Error sign convention: E_t = F_t − D_t** (positive = over-forecast, negative = under-forecast).
- **MSE** = average of E_t². Penalizes large errors heavily; use when big misses are very costly.
- **Absolute deviation** A_t = |E_t|. **MAD** = average of A_t. Use when the cost of error is proportional to its size.
- **σ of the random component ≈ 1.25 × MAD** (assumes normally distributed errors).
- **MAPE** = average of (|E_t| / D_t) × 100. Good when demand varies a lot between periods.
- **Bias** = Σ E_t. Should fluctuate around 0 if errors are random.
- **Tracking signal TS** = bias / MAD.
  - **TS outside ±6 → the forecast is biased.** TS < −6: consistent under-forecasting. TS > +6: consistent over-forecasting.
  - Typical causes: a method that ignores trend (e.g., MA on growing demand), or a sudden demand shift.
- **Measure error at the decision's lead time:** if orders need L weeks' notice, estimate the error of forecasts made L weeks ahead.
- Error within historical range → keep the method. Error well beyond history, or persistent bias → review the method or the demand pattern.

## 11. Choosing smoothing constants
- If the demand pattern is well understood, keep α (and β) **≤ 0.2**.
- Otherwise choose constants that minimize the preferred error measure (MSE by default; MAD or MAPE as alternatives), e.g., with Excel Solver.
- Avoid large constants for long periods; a larger constant is acceptable briefly when demand is in transition.
- Declining-alpha option: start with a high α after a demand shift, then let it decline to the long-run value.

## 12. Forecasting in practice
- **Collaborate** across functions and partners; use an S&OP process to bring sales and operations together.
- **Share only data that adds value.**
- **Distinguish demand from sales:** sales understate demand during stockouts and are inflated by promotions. Adjust for stockouts, competitor actions, pricing and promotions.
- **Promotions:** estimate what demand would have been without the promotion (baseline), then add the promotion effect separately.
- **Software helps** with volume, frequency and model selection, but must track historical errors and must not replace human judgment.

## 13. How this applies to our agent
- Our SKU-store weekly data is the least aggregated level, so expect large errors and report them.
- Little seasonality in 2.5 years of data → MA, SES and Holt are the right course methods; Winter's is not used.
- Promo uplift is a **causal** adjustment on top of a time-series baseline (Sections 4 and 12).
- Every forecast is reported with an error measure (Section 2, point 1).
- Errors use the course sign convention, E = F − D (Section 10).
- TS outside ±6 or MAPE above the policy threshold → flag for human review.
- The final order decision belongs to the planner (Section 4).
