"""The 7 tools the agent can call: JSON definitions for Claude + the Python that runs them.

Every number the agent reports must come from one of these tools.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from analytics.forecast import DATA, TRAIN_WEEKS, run_forecasts
from analytics.inventory import inventory_policy as _inventory_policy
from analytics.promo import PROMO_TYPES, promo_lift as _promo_lift

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"
DOC_FILES = sorted((KNOWLEDGE / "docs").glob("*.md")) + [KNOWLEDGE / "data_dictionary.md"]
POLICY_FILE = "forecasting_policy.md"

# Single source for policy numbers (stated in forecasting_policy.md).
POLICY = json.loads((KNOWLEDGE / "policy_values.json").read_text())
POLICY_SERVICE_LEVEL = {int(k): v for k, v in POLICY["service_level_by_sku"].items()}
SKUS = sorted(POLICY_SERVICE_LEVEL)  # covered SKUs = those with a policy service level
DEFAULT_HORIZON = POLICY["default_horizon_weeks"]
MAPE_REVIEW_PCT = POLICY["mape_review_threshold_pct"]
TS_REVIEW = POLICY["tracking_signal_limit"]
ADJUSTMENT_APPROVAL_PCT = POLICY["adjustment_approval_threshold_pct"]
TOLERANCE = 0.005  # validate: reported numbers must be within 0.5% of the recomputed value


class ToolError(Exception):
    """Raised for bad or out-of-scope inputs; returned to Claude as an error result."""


def _check_sku(sku_id):
    if int(sku_id) not in SKUS:
        raise ToolError(f"SKU {sku_id} is out of scope. Covered SKUs at store 8023: {SKUS}. "
                        "Escalate with request_human_review.")
    return int(sku_id)


# ---------- 1. search_knowledge ----------
STOPWORDS = set("the a an and or of for to in on is are be by with what which how does do at as it this that".split())


def _sections():
    """Split every knowledge doc into '## ' sections."""
    out = []
    for f in DOC_FILES:
        text = f.read_text()
        for part in re.split(r"\n(?=## )", text):
            heading = part.strip().splitlines()[0].lstrip("#").strip()
            out.append({"file": f.name, "section": heading, "text": part.strip()})
    return out


def search_knowledge(query, max_results=3):
    words = [w for w in re.findall(r"[a-z0-9%+.]+", query.lower()) if w not in STOPWORDS and len(w) > 1]
    scored = []
    for s in _sections():
        low = s["text"].lower()
        score = sum(low.count(w) for w in words)
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    results = [s for _, s in scored[:max_results]]
    if not results:
        return {"query": query, "results": [], "note": "No matching passage in the knowledge base."}
    return {"query": query, "results": results}


# ---------- 2. get_history ----------
def get_history(sku_id, last_n_weeks=12):
    sku_id = _check_sku(sku_id)
    df = pd.read_csv(DATA)
    g = df[df["sku_id"] == sku_id].sort_values("week_num")
    y = g["units_sold"]
    last4, prev12 = y.iloc[-4:].mean(), y.iloc[-16:-4].mean()
    recent = g.tail(int(last_n_weeks))
    return {
        "sku_id": sku_id,
        "store_id": 8023,
        "weeks": f"1-{len(g)} ({g['week'].iloc[0]} to {g['week'].iloc[-1]})",
        "units": "units/week",
        "summary_all_weeks": {
            "mean": round(float(y.mean()), 2), "std": round(float(y.std()), 2),
            "min": int(y.min()), "max": int(y.max()),
            "promo_weeks_any": int(((g["is_featured_sku"] == 1) | (g["is_display_sku"] == 1) | (g["discount"] >= 0.05)).sum()),
        },
        "recent_trend": {
            "avg_last_4_weeks": round(float(last4), 2),
            "avg_previous_12_weeks": round(float(prev12), 2),
            "change_pct": round(float((last4 / prev12 - 1) * 100), 1),
            "note": "Use this to check any trend the planner claims (e.g., 'sales are surging').",
        },
        f"last_{int(last_n_weeks)}_weeks": recent[["week_num", "week", "units_sold", "discount",
                                                  "is_featured_sku", "is_display_sku"]].to_dict("records"),
        "data_quality": "No missing weeks for this SKU. Sales are used as demand (stockouts not recorded). "
                        "See data_dictionary.md.",
    }


# ---------- 3. run_forecasts ----------
def tool_run_forecasts(sku_id, horizon_weeks=None, adjustment_pct=0.0):
    sku_id = _check_sku(sku_id)
    horizon_weeks = horizon_weeks or DEFAULT_HORIZON
    if not 1 <= int(horizon_weeks) <= 12:
        raise ToolError("horizon_weeks must be 1-12.")
    return run_forecasts(sku_id, horizon=int(horizon_weeks), adjustment_pct=float(adjustment_pct))


# ---------- 4. promo_lift ----------
def promo_lift(sku_id, promo_types=None):
    sku_id = _check_sku(sku_id)
    try:
        return _promo_lift(sku_id, promo_types or ["any"])
    except ValueError as e:
        raise ToolError(str(e))


# ---------- 5. inventory_policy ----------
def inventory_policy(sku_id, lead_time_weeks, service_level, adjustment_pct=0.0):
    """Runs the forecast itself so no numbers are copied by hand between tools."""
    sku_id = _check_sku(sku_id)
    L = int(lead_time_weeks)
    if not 1 <= L <= 12:
        raise ToolError("lead_time_weeks must be 1-12.")
    fc = run_forecasts(sku_id, horizon=max(L, DEFAULT_HORIZON), adjustment_pct=float(adjustment_pct))
    try:
        inv = _inventory_policy(fc["future_forecast"]["adjusted"], fc["sigma_error"], L, float(service_level))
    except ValueError as e:
        raise ToolError(str(e))
    return {
        "sku_id": sku_id,
        "selected_method": fc["selected_method"],
        **inv,
        "sigma_source": "1.25 x MAD of selected method, holdout fit (weeks 1-118)",
        "forecast_source": "refit (weeks 1-130)",
        "weekly_forecast_used": fc["future_forecast"]["adjusted"][:L],
        "adjustment_pct": float(adjustment_pct),
        "policy_service_level": POLICY_SERVICE_LEVEL[sku_id],
        "units": "safety stock, forecast over lead time and ROP in units",
    }


# ---------- 6. validate ----------
def _doc_service_level_conflicts(sku_id):
    """Find other documents that set a different service level for this SKU than the policy."""
    conflicts = []
    policy_pct = round(POLICY_SERVICE_LEVEL[sku_id] * 100)
    for f in DOC_FILES:
        if f.name == POLICY_FILE:
            continue
        for line in f.read_text().splitlines():
            if str(sku_id) in line and "service level" in line.lower():
                for pct in re.findall(r"(\d{2})\s*%", line):
                    if int(pct) != policy_pct:
                        conflicts.append({"file": f.name, "text": line.strip(),
                                          "value": f"{pct}%", "policy_file": POLICY_FILE,
                                          "policy_value": f"{policy_pct}%"})
    return conflicts


def _close(reported, actual):
    return abs(float(reported) - float(actual)) <= TOLERANCE * max(abs(float(actual)), 1.0)


def validate(sku_id, lead_time_weeks, service_level, adjustment_pct=0.0, promo_types=None,
             reported=None):
    """Recompute everything from scratch, compare with the numbers the agent plans to report,
    and apply the policy rules. reported: dict with any of selected_method, mape_pct,
    sigma_error, safety_stock_units, reorder_point_units."""
    sku_id = _check_sku(sku_id)
    reported = reported or {}
    fc = run_forecasts(sku_id, horizon=max(int(lead_time_weeks), DEFAULT_HORIZON), adjustment_pct=float(adjustment_pct))
    sel = fc["selected_method"]
    m = fc["methods"][sel]
    inv = inventory_policy(sku_id, lead_time_weeks, service_level, adjustment_pct)

    checks, review, approval = [], [], []

    # (a) reported numbers match recomputation
    truth = {"selected_method": sel, "mape_pct": m["mape_pct"], "sigma_error": fc["sigma_error"],
             "safety_stock_units": inv["safety_stock_units"], "reorder_point_units": inv["reorder_point_units"]}
    for k, v in reported.items():
        if k not in truth:
            continue
        ok = (v == truth[k]) if k == "selected_method" else _close(v, truth[k])
        checks.append({"check": f"reported {k} matches recomputation", "reported": v,
                       "recomputed": truth[k], "pass": bool(ok)})

    # (b) lowest-MAPE rule (recomputed independently of run_forecasts' choice)
    lowest = min(fc["methods"], key=lambda k: fc["methods"][k]["mape_pct"])
    checks.append({"check": "selected method has the lowest holdout MAPE", "pass": fc["methods"][lowest]["mape_pct"] == m["mape_pct"]})
    ties = [k for k, v in fc["methods"].items() if k != sel and v["mape_pct"] - m["mape_pct"] < 1.0]
    if ties:
        checks.append({"check": "practical tie (MAPE within 1 point)", "close_alternatives": ties, "pass": True})

    # (c) promo adjustment must equal promo_lift
    if float(adjustment_pct) != 0 or promo_types:
        lift = _promo_lift(sku_id, promo_types or ["any"])
        ok = lift["lift_pct"] is not None and _close(adjustment_pct, lift["lift_pct"])
        checks.append({"check": "adjustment equals promo_lift", "adjustment_pct": float(adjustment_pct),
                       "promo_lift_pct": lift["lift_pct"], "used_type": lift["used_type"], "pass": bool(ok)})
        if float(adjustment_pct) > ADJUSTMENT_APPROVAL_PCT:
            approval.append(f"Promo adjustment {adjustment_pct}% > +{ADJUSTMENT_APPROVAL_PCT}%: planner approval required before use.")
            review.append(f"Adjustment > +{ADJUSTMENT_APPROVAL_PCT}%")

    # (d) review triggers
    if m["mape_pct"] > MAPE_REVIEW_PCT:
        review.append(f"MAPE {m['mape_pct']}% > {MAPE_REVIEW_PCT}%")
    if abs(m["tracking_signal"]) > TS_REVIEW:
        review.append(f"|TS| {abs(m['tracking_signal'])} > {TS_REVIEW}")
    conflicts = _doc_service_level_conflicts(sku_id)
    if conflicts:
        review.append("Policy/memo conflict on service level")
    sl = float(service_level)
    if abs(sl - POLICY_SERVICE_LEVEL[sku_id]) > 1e-9:
        checks.append({"check": "service level matches policy", "used": sl,
                       "policy": POLICY_SERVICE_LEVEL[sku_id], "pass": False,
                       "note": "Different from policy; needs a documented reason or planner approval."})

    return {
        "sku_id": sku_id,
        "all_checks_pass": all(c["pass"] for c in checks),
        "checks": checks,
        "recomputed": {**truth, "tracking_signal": m["tracking_signal"], "fit": "holdout fit (weeks 1-118) for MAPE/sigma; refit (weeks 1-130) for forecast/ROP"},
        "human_review_required": bool(review),
        "review_reasons": review,
        "planner_approval_required": approval,
        "document_conflicts": conflicts,
        "next_step": ("Call request_human_review with these reasons." if review else "No review trigger."),
    }


# ---------- 7. request_human_review ----------
REVIEW_LOG = []  # simulated; the app shows it, nothing is sent anywhere


def request_human_review(sku_id, reasons, recommended_next_step=""):
    ticket = {"ticket_id": f"REV-{len(REVIEW_LOG) + 1:03d}", "sku_id": sku_id, "reasons": reasons,
              "recommended_next_step": recommended_next_step,
              "status": "SIMULATED - logged for the planner. No order placed, no supplier contacted."}
    REVIEW_LOG.append(ticket)
    return ticket


# ---------- Definitions sent to Claude ----------
SKU_PROP = {"type": "integer", "description": "SKU id. In scope: 217390, 219009, 223245 (store 8023)."}

TOOLS = [
    {"name": "search_knowledge",
     "description": "Keyword search over the knowledge base (forecasting policy, S&OP memo, course concepts, "
                    "project methods, data dictionary). Returns matching sections with file names to cite.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Keywords, e.g. '219009 service level' or 'tracking signal'."}},
         "required": ["query"]}},
    {"name": "get_history",
     "description": "Weekly sales history for a SKU at store 8023: summary stats, recent trend "
                    "(last 4 weeks vs previous 12), last N weeks with price/promo flags, data-quality notes.",
     "input_schema": {"type": "object", "properties": {
         "sku_id": SKU_PROP,
         "last_n_weeks": {"type": "integer", "description": "Recent weeks to list (default 12)."}},
         "required": ["sku_id"]}},
    {"name": "run_forecasts",
     "description": "Fits naive, MA(8), SES and Holt on weeks 1-118 and scores them on weeks 119-130 "
                    "(holdout fit: MAD, MAPE, bias, TS, sigma, fitted parameters). Selects the lowest MAPE, "
                    "refits it on weeks 1-130 and forecasts ahead (refit). Optional adjustment_pct for a promo.",
     "input_schema": {"type": "object", "properties": {
         "sku_id": SKU_PROP,
         "horizon_weeks": {"type": "integer", "description": "Weeks to forecast ahead, 1-12 (policy default 4)."},
         "adjustment_pct": {"type": "number", "description": "Promo adjustment %, must equal promo_lift output. Default 0."}},
         "required": ["sku_id"]}},
    {"name": "promo_lift",
     "description": "Historical promotion lift for a SKU: average units in promo weeks vs normal weeks, by type. "
                    "With several types, returns the largest single-type lift (never stacked).",
     "input_schema": {"type": "object", "properties": {
         "sku_id": SKU_PROP,
         "promo_types": {"type": "array", "items": {"type": "string", "enum": PROMO_TYPES},
                         "description": "Promo types named by the planner; use ['any'] if no type is stated."}},
         "required": ["sku_id"]}},
    {"name": "inventory_policy",
     "description": "Safety stock and reorder point: SS = z x sigma x sqrt(L), ROP = forecast over L + SS. "
                    "Runs the forecast itself (sigma from holdout fit, forecast from refit).",
     "input_schema": {"type": "object", "properties": {
         "sku_id": SKU_PROP,
         "lead_time_weeks": {"type": "integer", "description": "Replenishment lead time in weeks (1-12)."},
         "service_level": {"type": "number", "description": "Cycle service level as a fraction, e.g. 0.95."},
         "adjustment_pct": {"type": "number", "description": "Promo adjustment % (from promo_lift). Default 0."}},
         "required": ["sku_id", "lead_time_weeks", "service_level"]}},
    {"name": "validate",
     "description": "Recomputes the numbers from scratch and checks them against what you plan to report; "
                    "checks the lowest-MAPE rule, that the adjustment equals promo_lift, and the policy review "
                    "triggers (MAPE > 30%, |TS| > 6, document conflicts, adjustment > +50%). Call before answering.",
     "input_schema": {"type": "object", "properties": {
         "sku_id": SKU_PROP,
         "lead_time_weeks": {"type": "integer"},
         "service_level": {"type": "number"},
         "adjustment_pct": {"type": "number"},
         "promo_types": {"type": "array", "items": {"type": "string", "enum": PROMO_TYPES}},
         "reported": {"type": "object", "description": "Numbers you plan to report: selected_method, mape_pct, "
                                                       "sigma_error, safety_stock_units, reorder_point_units."}},
         "required": ["sku_id", "lead_time_weeks", "service_level"]}},
    {"name": "request_human_review",
     "description": "Logs a SIMULATED escalation to the planner / S&OP (no real email, order or supplier contact).",
     "input_schema": {"type": "object", "properties": {
         "sku_id": {"type": ["integer", "string"], "description": "SKU concerned, or 'n/a'."},
         "reasons": {"type": "array", "items": {"type": "string"}},
         "recommended_next_step": {"type": "string"}},
         "required": ["sku_id", "reasons"]}},
]

FUNCTIONS = {
    "search_knowledge": search_knowledge,
    "get_history": get_history,
    "run_forecasts": tool_run_forecasts,
    "promo_lift": promo_lift,
    "inventory_policy": inventory_policy,
    "validate": validate,
    "request_human_review": request_human_review,
}


def execute(name, args):
    """Run one tool. Returns (result_json_string, is_error)."""
    try:
        result = FUNCTIONS[name](**args)
        return json.dumps(result, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)), False
    except ToolError as e:
        return json.dumps({"error": str(e)}), True
    except (TypeError, ValueError, KeyError) as e:
        return json.dumps({"error": f"Bad input for {name}: {e}"}), True
