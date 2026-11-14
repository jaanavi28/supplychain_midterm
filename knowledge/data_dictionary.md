---
title: Data Dictionary
source: Written for this project by the owner.
version: v1, 2026-10-31
purpose: Describes the raw and prepared datasets, fields, units, periods, missing values, assumptions and preparation steps.
---

# Data Dictionary

## 1. Source
- **Raw file:** `knowledge/data/raw/train.csv`. Public retail demand forecasting dataset from Kaggle / Analytics Vidhya. **Public data, not synthetic.** It is never edited.
- Retail chain, 76 stores, weekly SKU-store sales, **17 Jan 2011 to 9 Jul 2013** (130 weeks), 150,150 rows.
- Only train.csv is used. test.csv and sample_submission.csv from the same download are **not used** (no actual sales).

## 2. Raw fields (train.csv)
| Field | Meaning | Units / format |
|---|---|---|
| record_ID | Row identifier | integer |
| week | Week start date | dd/mm/yy (parsed with an explicit format) |
| store_id | Store identifier | integer code |
| sku_id | Product identifier | integer code |
| total_price | Price actually charged that week | currency per unit (currency not stated) |
| base_price | Regular (list) price | currency per unit |
| is_featured_sku | SKU featured in promotion that week | 0/1 |
| is_display_sku | SKU on special display that week | 0/1 |
| units_sold | Units sold that week | units/week |

## 3. Prepared file: `knowledge/data/demand_store8023.csv`
Created by `scripts/prepare_data.py`. Store 8023 only; SKUs 217390, 219009, 223245; 130 weeks each (390 rows).

| Field | Meaning | Units |
|---|---|---|
| sku_id | Product | code |
| week_num | Week index 1–130 per SKU | integer |
| week | Week start date | YYYY-MM-DD |
| units_sold | Weekly sales (used as demand) | units/week |
| total_price, base_price | As in raw data | currency per unit |
| discount | (base_price − total_price) / base_price | fraction (0.15 = 15% off) |
| is_featured_sku, is_display_sku | As in raw data | 0/1 |

## 4. Preparation steps
1. Parse `week` as dd/mm/yy.
2. Fill missing `total_price` with `base_price` and log it.
3. Keep store 8023 and the 3 SKUs; sort by SKU and week; number weeks 1–130.
4. Add `discount`.
5. Export `verification/sku217390_series.csv` (week_num, week, units_sold, train/holdout split) for the independent Excel check.

## 5. Missing values and data quality
- **One missing `total_price`** in the whole raw file: record_ID 193915 (store 9436, SKU 245338, week of 23 Apr 2013). Filled with base_price. **It is not in store 8023, so the project data is unaffected.**
- No missing weeks for the 3 project SKUs (130 of 130 each).
- A few weeks have a slightly negative discount (price above base price): 1 week for 217390, 2 for 223245. Kept as is; treated as non-promo weeks.
- Many small discounts exist (e.g., 0.5%). Discounts under 5% are treated as normal price noise when measuring promo lift.

## 6. Assumptions and limitations
- **Sales are used as demand.** Sales understate demand in stockout weeks and are inflated by promotions (course doc, Section 12). Stockouts are not recorded in the data.
- **No product or store names**, so no category or location context is available.
- **Only 2.5 years of data**, so yearly seasonality is weak and cannot be estimated reliably (Winter's model not used).
- Weekly SKU-store is the least aggregated level, so forecast errors are expected to be large.
- Currency is not stated; prices are used only as ratios (discount).

## 7. How to update
- Replace or add raw files in `knowledge/data/raw/`, rerun `python scripts/prepare_data.py`, and add or update the row in `knowledge/inventory.csv`.
