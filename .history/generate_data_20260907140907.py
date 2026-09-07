"""
generate_data.py

Generates synthetic donation + demand history for the
Demand + Food Intelligence module.

Outputs:
    data/donations.csv
    data/demand.csv
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
np.random.seed(42)

# ---------- CONFIG ----------
NUM_RECIPIENTS = 15
NUM_DONORS = 25
NUM_DAYS = 180  # ~6 months of history
START_DATE = datetime.today() - timedelta(days=NUM_DAYS)

FOOD_CATEGORIES = [
    "cooked_meals", "rice_grains", "vegetables", "fruits",
    "bakery", "dairy", "packaged_snacks", "beverages"
]

SHELF_LIFE_DAYS = {
    "cooked_meals": 1,
    "rice_grains": 180,
    "vegetables": 5,
    "fruits": 5,
    "bakery": 3,
    "dairy": 4,
    "packaged_snacks": 90,
    "beverages": 60,
}

# ---------- ENTITIES ----------
recipients = [
    {
        "recipient_id": f"R{i+1:03d}",
        "name": fake.company() + " Shelter",
        "size": np.random.choice(["small", "medium", "large"], p=[0.4, 0.4, 0.2]),
    }
    for i in range(NUM_RECIPIENTS)
]

donors = [
    {
        "donor_id": f"D{i+1:03d}",
        "name": fake.company(),
        "type": np.random.choice(["restaurant", "grocery", "event", "household"]),
    }
    for i in range(NUM_DONORS)
]

SIZE_BASE_DEMAND = {"small": 20, "medium": 50, "large": 100}


# ---------- DEMAND GENERATION ----------
def generate_demand():
    rows = []
    for day_offset in range(NUM_DAYS):
        date = START_DATE + timedelta(days=day_offset)
        weekday = date.weekday()  # 0=Mon
        is_weekend = weekday >= 5

        for r in recipients:
            base = SIZE_BASE_DEMAND[r["size"]]

            # weekend bump, random noise, mild upward trend over time
            weekend_factor = 1.25 if is_weekend else 1.0
            trend_factor = 1 + (day_offset / NUM_DAYS) * 0.15
            noise = np.random.normal(1.0, 0.15)

            quantity = max(0, base * weekend_factor * trend_factor * noise)

            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "recipient_id": r["recipient_id"],
                "recipient_size": r["size"],
                "quantity_needed_kg": round(quantity, 1),
            })
    return pd.DataFrame(rows)


# ---------- DONATION GENERATION ----------
def generate_donations():
    rows = []
    donation_id = 1
    for day_offset in range(NUM_DAYS):
        date = START_DATE + timedelta(days=day_offset)
        num_donations_today = np.random.poisson(6)

        for _ in range(num_donations_today):
            donor = donors[np.random.randint(0, NUM_DONORS)]
            category = np.random.choice(FOOD_CATEGORIES)
            quantity = round(np.random.gamma(shape=2.0, scale=8.0), 1)  # skewed, mostly small batches

            rows.append({
                "donation_id": f"DN{donation_id:05d}",
                "date": date.strftime("%Y-%m-%d"),
                "donor_id": donor["donor_id"],
                "donor_type": donor["type"],
                "food_category": category,
                "quantity_kg": quantity,
                "shelf_life_days": SHELF_LIFE_DAYS[category],
            })
            donation_id += 1
    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    demand_df = generate_demand()
    donations_df = generate_donations()

    pd.DataFrame(recipients).to_csv("data/recipients.csv", index=False)
    pd.DataFrame(donors).to_csv("data/donors.csv", index=False)
    demand_df.to_csv("data/demand.csv", index=False)
    donations_df.to_csv("data/donations.csv", index=False)

    print(f"Generated {len(demand_df)} demand records -> data/demand.csv")
    print(f"Generated {len(donations_df)} donation records -> data/donations.csv")
    print("Also wrote data/recipients.csv and data/donors.csv")
