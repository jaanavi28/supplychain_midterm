---
title: Store Forecasting and Replenishment Policy
source: SYNTHETIC — written for this class project to simulate a company policy. Not a real company document.
version: v1, effective 2026-09-01
type: policy (synthetic)
purpose: Sets the service levels, method selection rule, promotion adjustment rule, human-review triggers and limits of authority the forecasting agent must follow.
---

# Store Forecasting and Replenishment Policy (SYNTHETIC)

> This is a synthetic document created for the BIA674 midterm project.

## 1. Scope
- Applies to weekly SKU forecasts and replenishment parameters at store 8023.
- Covered SKUs: 217390, 219009, 223245. Any other SKU is out of scope and goes to human review.

## 2. Service levels (cycle service level)
| SKU | Service level |
|---|---|
| 217390 | 95% |
| 219009 | 95% |
| 223245 | 90% |
| **Default** (if not stated by the planner) | **95%** |

- If the planner does not give a service level, use the SKU's level above and say so.

## 3. Forecast method selection
- Approved methods: naive, moving average MA(8), simple exponential smoothing (SES), Holt's model.
- Select the method with the **lowest holdout MAPE** (fixed-origin 12-week holdout). Naive may be selected.
- MAPE differences **under 1 percentage point are practical ties**. Still select the lowest, but report the tie and name the close alternatives.

## 4. Promotion adjustments
- A promotion adjustment **must equal the promo_lift tool output** for the matching promotion type (featured, display, discount, or "any" if no type is stated — state this as an assumption). No fixed cap and no judgmental numbers.
- **Never stack lifts.** If more than one promotion type is named (e.g., featured and discounted), use the **largest single-type lift** and say so.
- Adjustments **above +50% require planner approval** before the adjusted forecast is used for replenishment.
- State the promo type used, the number of promo weeks behind the lift, and whether the sample is small.

## 5. Human review triggers
Escalate for human review when any of these is true:
1. Selected method's holdout **MAPE > 30%**.
2. Selected method's **|tracking signal| > 6** (TS = bias / MAD).
3. A **conflict between this policy and another document** (e.g., an S&OP memo) on any parameter.
4. A promotion **adjustment > +50%**.
5. A request outside scope (SKU not covered, data not available, action beyond authority).

## 6. Limits of authority
- The agent recommends; the planner decides.
- The agent **never places orders, changes system parameters, or contacts suppliers**. Any such step is described as a simulated action that requires planner approval.
