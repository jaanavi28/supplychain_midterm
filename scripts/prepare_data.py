"""Prepare the Kaggle train.csv for the agent.

Reads knowledge/data/raw/train.csv (never modified), keeps store 8023 and the
3 project SKUs, fills the missing total_price, adds a discount column, and
writes:
  - knowledge/data/demand_store8023.csv   (used by the agent's tools)
  - verification/sku217390_series.csv     (for the independent Excel check)

Run from the repo root:  python scripts/prepare_data.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "knowledge" / "data" / "raw" / "train.csv"
OUT = ROOT / "knowledge" / "data" / "demand_store8023.csv"
VERIFY = ROOT / "verification" / "sku217390_series.csv"

STORE = 8023
SKUS = [217390, 219009, 223245]
TRAIN_WEEKS = 118  # weeks 1-118 train, 119-130 holdout


def main():
    df = pd.read_csv(RAW)
    print(f"Raw rows: {len(df)}")

    # Dates are dd/mm/yy; use an explicit format so day and month are never swapped.
    df["week"] = pd.to_datetime(df["week"], format="%d/%m/%y")

    # Data quality: fill missing total_price with base_price and log it.
    missing = df["total_price"].isna()
    for _, row in df[missing].iterrows():
        print(f"Filled missing total_price with base_price: record_ID={row.record_ID}, "
              f"store={row.store_id}, sku={row.sku_id}, week={row.week.date()}")
    df.loc[missing, "total_price"] = df.loc[missing, "base_price"]

    df = df[(df["store_id"] == STORE) & (df["sku_id"].isin(SKUS))].copy()
    df["discount"] = ((df["base_price"] - df["total_price"]) / df["base_price"]).round(4)
    df = df.sort_values(["sku_id", "week"])
    df["week_num"] = df.groupby("sku_id").cumcount() + 1

    cols = ["sku_id", "week_num", "week", "units_sold", "total_price", "base_price",
            "discount", "is_featured_sku", "is_display_sku"]
    df = df[cols]
    df["week"] = df["week"].dt.strftime("%Y-%m-%d")
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(df)} rows")
    print(df.groupby("sku_id")["week_num"].agg(["count", "min", "max"]))

    s = df[df["sku_id"] == 217390][["week_num", "week", "units_sold"]].copy()
    s["split"] = s["week_num"].apply(lambda w: "train" if w <= TRAIN_WEEKS else "holdout")
    VERIFY.parent.mkdir(exist_ok=True)
    s.to_csv(VERIFY, index=False)
    print(f"Wrote {VERIFY.relative_to(ROOT)}: {len(s)} rows")


if __name__ == "__main__":
    main()
