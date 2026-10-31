"""Safety stock and reorder point.

SS  = z * sigma_error * sqrt(L)      (sigma_error = std dev of the chosen method's 12 holdout errors)
ROP = forecast over lead time + SS   (forecast over lead time = sum of the next L weekly forecasts)
"""
import math
from statistics import NormalDist


def inventory_policy(weekly_forecast, sigma_error, lead_time_weeks, service_level):
    """weekly_forecast: list of future weekly forecasts (units/week), at least lead_time_weeks long.
    service_level: e.g. 0.95 for 95% cycle service level."""
    L = int(lead_time_weeks)
    if L < 1 or L > len(weekly_forecast):
        raise ValueError(f"lead_time_weeks must be 1..{len(weekly_forecast)} (forecast horizon)")
    if not 0.5 <= service_level < 1:
        raise ValueError("service_level must be between 0.5 and 1 (e.g. 0.95)")
    z = NormalDist().inv_cdf(service_level)
    ss = z * sigma_error * math.sqrt(L)
    lt_demand = sum(weekly_forecast[:L])
    return {
        "service_level": service_level,
        "z": round(z, 4),
        "sigma_error_units_per_week": sigma_error,
        "lead_time_weeks": L,
        "safety_stock_units": round(ss, 1),
        "forecast_over_lead_time_units": round(lt_demand, 1),
        "reorder_point_units": round(lt_demand + ss, 1),
    }
