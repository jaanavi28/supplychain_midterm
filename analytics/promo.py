"""Historical promotion lift (causal adjustment on top of the time-series baseline).

Uses all 130 weeks of a SKU at store 8023.
  normal week   = not featured, not on display, discount < 5%
  promo week    = has the promo type asked for (featured / display / discount >= 5% / any of these)
  lift %        = (average units in promo weeks / average units in normal weeks - 1) x 100
"""
from analytics.forecast import DATA

import pandas as pd

DISCOUNT_MIN = 0.05  # discounts below 5% are treated as normal price noise
MIN_WEEKS = 5        # fewer promo weeks than this = low-confidence lift
PROMO_TYPES = ["featured", "display", "discount", "any"]


def promo_lift(sku_id, promo_type="any"):
    if promo_type not in PROMO_TYPES:
        raise ValueError(f"promo_type must be one of {PROMO_TYPES}")
    df = pd.read_csv(DATA)
    g = df[df["sku_id"] == sku_id]
    flags = {
        "featured": g["is_featured_sku"] == 1,
        "display": g["is_display_sku"] == 1,
        "discount": g["discount"] >= DISCOUNT_MIN,
    }
    flags["any"] = flags["featured"] | flags["display"] | flags["discount"]
    normal = g[~flags["any"]]["units_sold"]

    table = {}
    for t in PROMO_TYPES:
        promo = g[flags[t]]["units_sold"]
        table[t] = {
            "promo_weeks": int(len(promo)),
            "avg_units_promo": round(float(promo.mean()), 2) if len(promo) else None,
            "lift_pct": round(float((promo.mean() / normal.mean() - 1) * 100), 1) if len(promo) else None,
            "low_sample": len(promo) < MIN_WEEKS,
        }
    return {
        "sku_id": sku_id,
        "weeks_used": "1-130",
        "normal_weeks": int(len(normal)),
        "avg_units_normal": round(float(normal.mean()), 2),
        "definition": "normal = not featured, not display, discount < 5%; lift = promo avg / normal avg - 1",
        "by_type": table,
        "requested_type": promo_type,
        "lift_pct": table[promo_type]["lift_pct"],
        "note": "Promo types overlap (a week can be featured and discounted), so lifts are not additive.",
    }
