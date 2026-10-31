"""Forecasting methods and holdout accuracy (course conventions, Chopra Ch. 7).

Holdout is fixed-origin: fit on weeks 1-118, forecast weeks 119-130 in one shot.
Error E = F - D (positive = over-forecast). Bias = sum of E. TS = bias / MAD.
sigma for safety stock = 1.25 x MAD of the selected method's holdout errors.
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "knowledge" / "data" / "demand_store8023.csv"
TRAIN_WEEKS = 118
HOLDOUT_WEEKS = 12
METHODS = ["naive", "ma8", "ses", "holt"]  # also the tie-break order: simpler method wins a tie
GRID = np.round(np.arange(0.01, 1.00, 0.01), 2)  # smoothing constants 0.01..0.99


def load_series(sku_id):
    """Weekly units_sold for one SKU, ordered week 1..130."""
    df = pd.read_csv(DATA)
    return df[df["sku_id"] == sku_id].sort_values("week_num")["units_sold"].to_numpy(dtype=float)


def ses_in_sample(y, alpha, L0):
    """One-step-ahead SES forecasts F_t = L_(t-1). Returns (forecasts, final level)."""
    L, f = L0, []
    for d in y:
        f.append(L)
        L = alpha * d + (1 - alpha) * L
    return np.array(f), L


def holt_in_sample(y, alpha, beta, L0, T0):
    """One-step-ahead Holt forecasts F_t = L_(t-1) + T_(t-1). Returns (forecasts, final level, final trend)."""
    L, T, f = L0, T0, []
    for d in y:
        f.append(L + T)
        L_new = alpha * d + (1 - alpha) * (L + T)
        T = beta * (L_new - L) + (1 - beta) * T
        L = L_new
    return np.array(f), L, T


def fit_and_forecast(method, y, horizon):
    """Fit one method on y and forecast `horizon` weeks. Returns (forecast array, fitted parameters)."""
    if method == "naive":
        return np.repeat(y[-1], horizon), {}
    if method == "ma8":
        return np.repeat(y[-8:].mean(), horizon), {}
    if method == "ses":
        L0 = y.mean()  # course: L0 = average of the fitting data
        mse = [np.mean((ses_in_sample(y, a, L0)[0] - y) ** 2) for a in GRID]
        alpha = GRID[int(np.argmin(mse))]
        _, L = ses_in_sample(y, alpha, L0)
        params = {"alpha": float(alpha), "L0": round(float(L0), 4),
                  "final_level": round(float(L), 4), "in_sample_mse": round(float(min(mse)), 2)}
        return np.repeat(L, horizon), params
    # Holt: L0, T0 from regressing demand on t = 1..n (course: T0 = slope, L0 = intercept)
    t = np.arange(1, len(y) + 1)
    T0, L0 = np.polyfit(t, y, 1)
    best = None
    for a in GRID:
        for b in GRID:
            mse = np.mean((holt_in_sample(y, a, b, L0, T0)[0] - y) ** 2)
            if best is None or mse < best[0]:
                best = (mse, a, b)
    mse, alpha, beta = best
    _, L, T = holt_in_sample(y, alpha, beta, L0, T0)
    params = {"alpha": float(alpha), "beta": float(beta), "L0": round(float(L0), 4),
              "T0": round(float(T0), 4), "final_level": round(float(L), 4),
              "final_trend": round(float(T), 4), "in_sample_mse": round(float(mse), 2)}
    return L + T * np.arange(1, horizon + 1), params


def accuracy(actual, forecast):
    """Course error measures with E = F - D."""
    err = forecast - actual
    mad = np.mean(np.abs(err))
    bias = err.sum()
    return {
        "mad": round(float(mad), 2),
        "mape_pct": round(float(np.mean(np.abs(err) / actual) * 100), 2),
        "bias": round(float(bias), 2),
        "tracking_signal": round(float(bias / mad), 2),
        "sigma_error": round(float(1.25 * mad), 2),  # course: sigma ~= 1.25 x MAD
    }


def run_forecasts(sku_id, horizon=4, adjustment_pct=0.0):
    """Evaluate all methods on the holdout, select the lowest MAPE, then refit the
    selected method on all 130 weeks to forecast the next `horizon` weeks.
    adjustment_pct (e.g. 20 for +20%) is applied to the future forecast only."""
    y = load_series(sku_id)
    train, holdout = y[:TRAIN_WEEKS], y[TRAIN_WEEKS:]

    results = {}
    for m in METHODS:
        fc, params = fit_and_forecast(m, train, HOLDOUT_WEEKS)
        results[m] = {"fit": "holdout fit (weeks 1-118)", **accuracy(holdout, fc), "params": params,
                      "holdout_forecast": [round(float(v), 2) for v in fc]}

    # Lowest MAPE wins; ties go to the simpler method (METHODS order).
    selected = min(METHODS, key=lambda m: (results[m]["mape_pct"], METHODS.index(m)))

    future, future_params = fit_and_forecast(selected, y, horizon)
    adjusted = future * (1 + adjustment_pct / 100)
    return {
        "sku_id": sku_id,
        "train_weeks": "1-118",
        "holdout_weeks": "119-130",
        "error_convention": "E = F - D; bias = sum(E); TS = bias / MAD; sigma = 1.25 x MAD",
        "holdout_actual": [int(v) for v in holdout],
        "methods": results,
        "selected_method": selected,
        "selection_rule": "lowest holdout MAPE; ties go to the simpler method",
        "sigma_error": results[selected]["sigma_error"],
        "sigma_error_fit": "holdout fit (weeks 1-118)",
        "future_forecast": {
            "fit": "refit (weeks 1-130)",
            "weeks": f"131-{130 + horizon}",
            "params": future_params,
            "base": [round(float(v), 2) for v in future],
            "adjustment_pct": adjustment_pct,
            "adjusted": [round(float(v), 2) for v in adjusted],
        },
    }
