"""Forecasting methods and holdout accuracy.

Holdout is fixed-origin: fit on weeks 1-118, forecast weeks 119-130 in one shot.
Error = actual - forecast (positive error = forecast too low).
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

DATA = Path(__file__).resolve().parent.parent / "knowledge" / "data" / "demand_store8023.csv"
TRAIN_WEEKS = 118
HOLDOUT_WEEKS = 12
METHODS = ["naive", "ma8", "ses", "holt"]  # also the tie-break order: simpler method wins a tie


def load_series(sku_id):
    """Weekly units_sold for one SKU, ordered week 1..130."""
    df = pd.read_csv(DATA)
    return df[df["sku_id"] == sku_id].sort_values("week_num")["units_sold"].to_numpy(dtype=float)


def fit_and_forecast(method, y, horizon):
    """Fit one method on y and forecast `horizon` weeks. Returns (forecast array, fitted parameters)."""
    if method == "naive":
        return np.repeat(y[-1], horizon), {}
    if method == "ma8":
        return np.repeat(y[-8:].mean(), horizon), {}
    trend = "add" if method == "holt" else None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(y, trend=trend, initialization_method="estimated").fit()
    p = fit.params
    params = {"alpha": round(float(p["smoothing_level"]), 4),
              "initial_level": round(float(p["initial_level"]), 4)}
    if method == "holt":
        params["beta"] = round(float(p["smoothing_trend"]), 4)
        params["initial_trend"] = round(float(p["initial_trend"]), 4)
    return np.asarray(fit.forecast(horizon)), params


def accuracy(actual, forecast):
    """MAE, MAPE (%), bias (mean error), tracking signal (sum of errors / MAD)."""
    err = actual - forecast
    mae = np.mean(np.abs(err))
    return {
        "mae": round(float(mae), 2),
        "mape_pct": round(float(np.mean(np.abs(err) / actual) * 100), 2),
        "bias": round(float(err.mean()), 2),
        "tracking_signal": round(float(err.sum() / mae), 2),
        "sigma_error": round(float(np.std(err, ddof=1)), 2),  # sample std dev (Excel STDEV.S)
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
        results[m] = {**accuracy(holdout, fc), "params": params,
                      "holdout_forecast": [round(float(v), 2) for v in fc]}

    # Lowest MAPE wins; ties go to the simpler method (METHODS order).
    selected = min(METHODS, key=lambda m: (results[m]["mape_pct"], METHODS.index(m)))

    future, future_params = fit_and_forecast(selected, y, horizon)
    adjusted = future * (1 + adjustment_pct / 100)
    return {
        "sku_id": sku_id,
        "train_weeks": "1-118",
        "holdout_weeks": "119-130",
        "holdout_actual": [int(v) for v in holdout],
        "methods": results,
        "selected_method": selected,
        "selection_rule": "lowest holdout MAPE; ties go to the simpler method",
        "sigma_error": results[selected]["sigma_error"],
        "future_forecast": {
            "weeks": f"131-{130 + horizon}",
            "fitted_on": "weeks 1-130",
            "params": future_params,
            "base": [round(float(v), 2) for v in future],
            "adjustment_pct": adjustment_pct,
            "adjusted": [round(float(v), 2) for v in adjusted],
        },
    }
