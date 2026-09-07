from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from .generate_synthetic_data import (
    DATA_DIR,
    FOOD_TYPES,
    PERISHABILITY_BY_FOOD,
    UNITS_BY_FOOD,
    DONOR_TYPES,
)

REQUIRED_COLUMNS = [
    "donation_id",
    "donor_type",
    "food_type",
    "quantity",
    "unit",
    "latitude",
    "longitude",
    "vegetarian",
    "vegan",
    "perishability",
    "hours_until_expiry",
    "pickup_required",
]

LAT_BOUNDS = (26.5, 27.3)
LON_BOUNDS = (75.4, 76.2)

class ValidationError(ValueError):
    pass

def _next_donation_id(existing: pd.DataFrame) -> str:
    if existing.empty:
        return "D0001"
    nums = (
        existing["donation_id"]
        .astype(str)
        .str.extract(r"D(\d+)", expand=False)
        .dropna()
        .astype(int)
    )
    next_n = (nums.max() + 1) if not nums.empty else 1
    return f"D{next_n:04d}"

def validate_coords(lat: float, lon: float, *, strict_bounds: bool = False) -> None:
    if not (-90 <= lat <= 90):
        raise ValidationError(f"latitude {lat} out of range [-90, 90]")
    if not (-180 <= lon <= 180):
        raise ValidationError(f"longitude {lon} out of range [-180, 180]")
    if strict_bounds:
        if not (LAT_BOUNDS[0] <= lat <= LAT_BOUNDS[1]):
            raise ValidationError(
                f"latitude {lat} outside expected service area {LAT_BOUNDS}"
            )
        if not (LON_BOUNDS[0] <= lon <= LON_BOUNDS[1]):
            raise ValidationError(
                f"longitude {lon} outside expected service area {LON_BOUNDS}"
            )

def register_donation(
    *,
    food_type: str,
    quantity: float,
    lat: float,
    lon: float,
    hours_until_expiry: float,
    unit: str | None = None,
    perishability: str | None = None,
    donor_type: str = "restaurant",
    vegetarian: int = 1,
    vegan: int = 0,
    pickup_required: int = 1,
    data_dir: Path | str = DATA_DIR,
    strict_bounds: bool = False,
) -> dict:
    if food_type not in FOOD_TYPES:
        raise ValidationError(
            f"food_type '{food_type}' not recognized; expected one of {FOOD_TYPES}"
        )
    if donor_type not in DONOR_TYPES:
        raise ValidationError(
            f"donor_type '{donor_type}' not recognized; expected one of {DONOR_TYPES}"
        )
    if quantity <= 0:
        raise ValidationError("quantity must be positive")
    if hours_until_expiry <= 0:
        raise ValidationError("hours_until_expiry must be positive")

    validate_coords(lat, lon, strict_bounds=strict_bounds)

    unit = unit or UNITS_BY_FOOD.get(food_type, "meals")
    perishability = perishability or PERISHABILITY_BY_FOOD.get(food_type, "medium")

    data_dir = Path(data_dir)
    donations_path = data_dir / "donations.csv"

    if donations_path.exists():
        existing = pd.read_csv(donations_path)
        existing.columns = existing.columns.str.strip()
    else:
        existing = pd.DataFrame(columns=REQUIRED_COLUMNS)

    new_row = {
        "donation_id": _next_donation_id(existing),
        "donor_type": donor_type,
        "food_type": food_type,
        "quantity": quantity,
        "unit": unit,
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "vegetarian": vegetarian,
        "vegan": vegan,
        "perishability": perishability,
        "hours_until_expiry": hours_until_expiry,
        "pickup_required": pickup_required,
    }

    updated = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(donations_path, index=False)

    return new_row

def main() -> None:
    parser = argparse.ArgumentParser(description="Register a new donor/donation by coordinates")
    parser.add_argument("--food-type", required=True, choices=FOOD_TYPES)
    parser.add_argument("--quantity", type=float, required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--hours-until-expiry", type=float, required=True)
    parser.add_argument("--unit", choices=["meals", "kg"], default=None)
    parser.add_argument("--perishability", choices=["low", "medium", "high"], default=None)
    parser.add_argument("--donor-type", choices=DONOR_TYPES, default="restaurant")
    parser.add_argument("--vegetarian", type=int, choices=[0, 1], default=1)
    parser.add_argument("--vegan", type=int, choices=[0, 1], default=0)
    parser.add_argument("--data-dir", type=str, default=str(DATA_DIR))
    parser.add_argument(
        "--strict-bounds",
        action="store_true",
        help="Reject coordinates outside the expected Jaipur service area",
    )
    args = parser.parse_args()

    row = register_donation(
        food_type=args.food_type,
        quantity=args.quantity,
        lat=args.lat,
        lon=args.lon,
        hours_until_expiry=args.hours_until_expiry,
        unit=args.unit,
        perishability=args.perishability,
        donor_type=args.donor_type,
        vegetarian=args.vegetarian,
        vegan=args.vegan,
        data_dir=args.data_dir,
        strict_bounds=args.strict_bounds,
    )

    print("Registered new donation:")
    for k, v in row.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()