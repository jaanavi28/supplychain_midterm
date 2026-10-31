---
title: Project Forecasting Definitions (store 8023)
source: Written for this project by the owner; implemented in analytics/forecast.py and analytics/inventory.py.
version: v1, 2026-10-31
type: project-specific method definitions (not synthetic data)
purpose: Defines how this project tests, selects and uses forecasts. General course definitions and formulas are in course_forecasting_concepts.md.
---

# Project Forecasting Definitions

General definitions, method formulas (moving average, SES, Holt), error measures and the
tracking-signal rule are in **course_forecasting_concepts.md**. This file only covers choices
specific to this project.

## 1. Data and time unit
- Weekly units sold for store 8023, SKUs 217390, 219009, 223245: 130 weeks (17 Jan 2011 to 9 Jul 2013).
- All forecasts, errors and σ are in **units per week**. Lead time is in **weeks**.

## 2. Fixed-origin holdout
- Fit each method on **weeks 1–118**, then forecast **weeks 119–130 (12 weeks) in one shot** from week 118.
- Forecasts are not updated with holdout actuals.
- Naive = demand in week 118, repeated for all 12 weeks.
- MA(8) = average of weeks 111–118, repeated for all 12 weeks.
- SES and Holt use the course formulas, with their final level (and trend) at week 118:
  - SES forecast = L_118 for every holdout week.
  - Holt forecast for week 118 + n = L_118 + n · T_118.

## 3. Fitting SES and Holt
- **SES:** L0 = average of the fitting weeks. α is the value from 0.01 to 0.99 (step 0.01) that gives the lowest in-sample MSE of one-step-ahead forecasts.
- **Holt:** L0 (intercept) and T0 (slope) come from a linear regression of the fitting weeks on t = 1, 2, …. α and β are the pair from the same grid with the lowest in-sample MSE.
- The tool reports α, β, L0 and T0 so the results can be reproduced in Excel.

## 4. Error measures (course convention)
- E = F − D (positive = over-forecast).
- MAD, MAPE, bias = ΣE and tracking signal = bias / MAD, all computed over the 12 holdout weeks.

## 5. Method selection rule
- The method with the **lowest holdout MAPE** is selected. Naive is allowed to win.
- MAPE is compared at 2 decimal places; an exact tie goes to the simpler method (naive, then MA(8), then SES, then Holt).

## 6. Forecast for future weeks
- The selected method is refit on **all 130 weeks** and forecasts weeks 131 onward.
- An optional judgmental adjustment % (e.g., a promotion) is applied on top of this baseline. It must be supported by the promo_lift tool and stay within the policy cap.

## 7. σ and safety stock
- **σ = 1.25 × MAD** of the selected method's 12 holdout errors (course approximation, assumes normal errors), in units/week.
- **Safety stock SS = z · σ · √L**, where z is the standard normal value for the cycle service level and L is the lead time in weeks.
- **Forecast over lead time** = sum of the next L weekly forecasts (after any adjustment).
- **Reorder point ROP = forecast over lead time + SS**, in units.
