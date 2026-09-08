"""
generate_recipients_from_ngos.py

Replaces the old generate_data.py, which was DANGEROUS: it wrote
data/donations.csv in a completely different, incompatible schema
(donation_id/date/donor_id/food_category/quantity_kg/shelf_life_days)
that would silently overwrite the real donations.csv the backend and
frontend actually use (donation_id/donor_type/food_type/quantity/unit/
latitude/longitude/vegetarian/vegan/perishability/hours_until_expiry/
pickup_required), breaking the whole platform on the next run. It also
invented fake "R001"-style recipients with no relationship to the real
NGOs in data/ngos.csv, so /predict/demand could never resolve a real
ngo_id.

This script does the same job (build training data for the demand
model) without either problem: it reads the real data/ngos.csv and
writes ONLY data/recipients.csv + data/demand.csv, with
recipient_id == ngo_id -- so /predict/demand can be called with the
same id used everywhere else in the system, no id-mapping table
needed. It never touches donations.csv or ngos.csv.

Run once (and again whenever data/ngos.csv changes materially) before
train_model.py:

    python generate_recipients_from_ngos.py
    python train_model.py

Demand history is still synthetic -- there's no real historical
fulfilment log yet. The base daily demand is derived from each NGO's
actual max_capacity_kg / max_capacity_meals instead of a random
small/medium/large draw, so predictions land in the right ballpark
per-NGO from day one. Swap this generator out once real
pickup/fulfilment records exist.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"

NUM_DAYS = 180
AVG_MEALS_PER_KG = 3.0  # rough blended factor across food_intelligence.MEALS_PER_KG


def _size_bucket(capacity_kg: float) -> str:
    if capacity_kg < 60:
        return "small"
    elif capacity_kg < 150:
        return "medium"
    return "large"


def build_recipients(ngos: pd.DataFrame) -> pd.DataFrame:
    ngos = ngos.copy()
    capacity_kg_equiv = pd.to_numeric(ngos.get("max_capacity_kg", 0), errors="coerce").fillna(0) + (
        pd.to_numeric(ngos.get("max_capacity_meals", 0), errors="coerce").fillna(0) / AVG_MEALS_PER_KG
    )
    return pd.DataFrame(
        {
            "recipient_id": ngos["ngo_id"],  # same id space as the rest of the system
            "name": ngos["ngo_name"],
            "size": capacity_kg_equiv.apply(_size_bucket),
            "capacity_kg_equiv": capacity_kg_equiv.round(1),  # kept for transparency/debugging
        }
    )


def build_demand_history(recipients: pd.DataFrame, num_days: int = NUM_DAYS, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start_date = datetime.today() - timedelta(days=num_days)

    rows = []
    for day_offset in range(num_days):
        date = start_date + timedelta(days=day_offset)
        is_weekend = date.weekday() >= 5

        for _, r in recipients.iterrows():
            base = max(5.0, r["capacity_kg_equiv"] * 0.35)
            weekend_factor = 1.25 if is_weekend else 1.0
            trend_factor = 1 + (day_offset / num_days) * 0.15
            noise = rng.normal(1.0, 0.15)
            quantity = max(0.0, base * weekend_factor * trend_factor * noise)

            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "recipient_id": r["recipient_id"],
                    "recipient_size": r["size"],
                    "quantity_needed_kg": round(quantity, 1),
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ngos-csv",
        default=str(DEFAULT_DATA_DIR / "ngos.csv"),
        help="Path to ngos.csv (default: data/ngos.csv, the shared source of truth)",
    )
    parser.add_argument(
        "--out-dir", default=str(DEFAULT_DATA_DIR), help="Output dir (default: data/)"
    )
    args = parser.parse_args()

    ngos_df = pd.read_csv(args.ngos_csv)
    ngos_df.columns = ngos_df.columns.str.strip()

    recipients_df = build_recipients(ngos_df)
    demand_df = build_demand_history(recipients_df)

    os.makedirs(args.out_dir, exist_ok=True)
    recipients_df[["recipient_id", "name", "size"]].to_csv(
        os.path.join(args.out_dir, "recipients.csv"), index=False
    )
    demand_df.to_csv(os.path.join(args.out_dir, "demand.csv"), index=False)

    print(f"Wrote {len(recipients_df)} recipients -> {args.out_dir}/recipients.csv (recipient_id == ngo_id)")
    print(f"Wrote {len(demand_df)} demand records -> {args.out_dir}/demand.csv")
    print("Next: run train_model.py to produce models/demand_model.pkl")
