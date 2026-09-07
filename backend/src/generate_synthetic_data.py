from __future__ import annotations
import argparse
import random
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DONOR_HUBS = {
    "C-Scheme": (26.9124, 75.7873),
    "MI_Road": (26.9196, 75.8067),
    "Malviya_Nagar": (26.8535, 75.8081),
    "Vaishali_Nagar": (26.9137, 75.7368),
    "Tonk_Road": (26.8467, 75.8055),
    "Jagatpura": (26.8189, 75.8420),
    "Raja_Park": (26.9058, 75.8285),
    "Civil_Lines": (26.9152, 75.7690),
}

NGO_HUBS = {
    "Sanganer": (26.8180, 75.8010),
    "Bapu_Nagar": (26.8890, 75.8130),
    "Shastri_Nagar": (26.9370, 75.7940),
    "Jhotwara": (26.9530, 75.7440),
    "Mansarovar": (26.8580, 75.7620),
    "Adarsh_Nagar": (26.8980, 75.8250),
}

FOOD_TYPES = ["cooked_meal", "packaged_food", "fruits", "vegetables", "bakery"]
UNITS_BY_FOOD = {
    "cooked_meal": "meals",
    "packaged_food": "meals",
    "bakery": "meals",
    "fruits": "kg",
    "vegetables": "kg",
}
PERISHABILITY_BY_FOOD = {
    "cooked_meal": "high",
    "bakery": "high",
    "packaged_food": "low",
    "fruits": "medium",
    "vegetables": "medium",
}

DONOR_TYPES = ["restaurant", "hotel", "caterer", "event", "household", "institution"]

def _jitter(center: tuple[float, float], spread_km: float, rng: random.Random) -> tuple[float, float]:
    lat, lon = center
    dlat = (rng.uniform(-spread_km, spread_km)) / 111.0
    dlon = (rng.uniform(-spread_km, spread_km)) / (111.0 * np.cos(np.radians(lat)))
    return round(lat + dlat, 6), round(lon + dlon, 6)

def generate_ngos(n: int = 40, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    hub_names = list(NGO_HUBS.keys())
    rows = []
    for i in range(1, n + 1):
        hub = NGO_HUBS[hub_names[(i - 1) % len(hub_names)]]
        lat, lon = _jitter(hub, spread_km=2.5, rng=rng)
        n_types = rng.randint(2, 4)
        accepted = rng.sample(FOOD_TYPES, n_types)
        food_types_str = "|".join(accepted)

        vegetarian = 1
        vegan = rng.choice([0, 1])

        max_cap_meals = rng.choice([80, 100, 120, 150, 200, 250])
        current_demand_meals = int(max_cap_meals * rng.uniform(0.2, 0.85))

        max_cap_kg = rng.choice([0, 60, 100, 150, 200, 250])
        current_demand_kg = int(max_cap_kg * rng.uniform(0.2, 0.85)) if max_cap_kg else 0

        pickup_radius = rng.choice([6, 8, 10, 12, 15, 18, 20])
        reliability = round(rng.uniform(0.75, 0.98), 2)

        rows.append(
            {
                "ngo_id": f"NGO{i:03d}",
                "ngo_name": f"{hub_names[(i - 1) % len(hub_names)].replace('_', ' ')} Relief Center {i}",
                "latitude": lat,
                "longitude": lon,
                "food_types": food_types_str,
                "vegetarian": vegetarian,
                "vegan": vegan,
                "current_demand_meals": current_demand_meals,
                "max_capacity_meals": max_cap_meals,
                "current_demand_kg": current_demand_kg,
                "max_capacity_kg": max_cap_kg,
                "pickup_radius_km": pickup_radius,
                "reliability_score": reliability,
            }
        )

    return pd.DataFrame(rows)

def generate_donations(n: int = 300, seed: int = 7) -> pd.DataFrame:
    rng = random.Random(seed)
    hub_names = list(DONOR_HUBS.keys())
    rows = []

    for i in range(1, n + 1):
        hub = DONOR_HUBS[hub_names[(i - 1) % len(hub_names)]]
        lat, lon = _jitter(hub, spread_km=1.8, rng=rng)

        food_type = rng.choice(FOOD_TYPES)
        unit = UNITS_BY_FOOD[food_type]
        perishability = PERISHABILITY_BY_FOOD[food_type]

        if unit == "meals":
            quantity = rng.choice([20, 30, 50, 75, 100, 120, 150, 200])
        else:
            quantity = rng.choice([15, 25, 40, 60, 80, 100, 150])
        if perishability == "high":
            hours_until_expiry = rng.choice([1, 2, 3, 4, 6])
        elif perishability == "medium":
            hours_until_expiry = rng.choice([6, 12, 18, 24, 30])
        else:
            hours_until_expiry = rng.choice([24, 48, 72, 96])

        vegetarian = 1 if food_type != "cooked_meal" else rng.choice([0, 1])
        vegan = 1 if food_type in ("fruits", "vegetables") else rng.choice([0, 1])

        rows.append(
            {
                "donation_id": f"D{i:04d}",
                "donor_type": rng.choice(DONOR_TYPES),
                "food_type": food_type,
                "quantity": quantity,
                "unit": unit,
                "latitude": lat,
                "longitude": lon,
                "vegetarian": vegetarian,
                "vegan": vegan,
                "perishability": perishability,
                "hours_until_expiry": hours_until_expiry,
                "pickup_required": 1,
            }
        )

    return pd.DataFrame(rows)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic SharePlate datasets")
    parser.add_argument("--donations", type=int, default=300, help="Number of donation rows")
    parser.add_argument("--ngos", type=int, default=40, help="Number of NGO rows")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--out-dir", type=str, default=str(DATA_DIR), help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    donations_df = generate_donations(n=args.donations, seed=args.seed)
    ngos_df = generate_ngos(n=args.ngos, seed=args.seed + 1)

    donations_path = out_dir / "donations.csv"
    ngos_path = out_dir / "ngos.csv"

    donations_df.to_csv(donations_path, index=False)
    ngos_df.to_csv(ngos_path, index=False)

    print(f"Wrote {len(donations_df)} donations -> {donations_path}")
    print(f"Wrote {len(ngos_df)} NGOs -> {ngos_path}")


if __name__ == "__main__":
    main()