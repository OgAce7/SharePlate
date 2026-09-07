"""
food_intelligence.py

Rule-based + lightweight logic for scoring individual donations:
- shelf life lookup
- estimated meals produced
- waste risk score (0-1, higher = more urgent to match)
"""

from datetime import datetime

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

# rough kg -> meals conversion factors by category
# (tunable; these are reasonable placeholder estimates)
MEALS_PER_KG = {
    "cooked_meals": 2.5,
    "rice_grains": 4.0,
    "vegetables": 3.0,
    "fruits": 3.5,
    "bakery": 3.0,
    "dairy": 2.0,
    "packaged_snacks": 5.0,
    "beverages": 4.0,
}


def get_shelf_life(food_category: str) -> int:
    return SHELF_LIFE_DAYS.get(food_category, 3)  # default: assume perishable


def estimate_meals(food_category: str, quantity_kg: float) -> float:
    factor = MEALS_PER_KG.get(food_category, 2.5)
    return round(quantity_kg * factor, 1)


def waste_risk_score(food_category: str, hours_since_donation: float) -> float:
    """
    Returns a 0-1 score. Higher = more urgent to match before spoilage.
    Based on what fraction of shelf life has already elapsed.
    """
    shelf_life_hours = get_shelf_life(food_category) * 24
    if shelf_life_hours <= 0:
        return 1.0
    fraction_elapsed = hours_since_donation / shelf_life_hours
    return round(min(1.0, max(0.0, fraction_elapsed)), 3)


def score_donation(food_category: str, quantity_kg: float, donation_timestamp: str) -> dict:
    """
    Main entry point. donation_timestamp: ISO format string, e.g. '2026-09-01T10:00:00'
    """
    donated_at = datetime.fromisoformat(donation_timestamp)
    hours_elapsed = (datetime.now() - donated_at).total_seconds() / 3600

    return {
        "food_category": food_category,
        "quantity_kg": quantity_kg,
        "shelf_life_days": get_shelf_life(food_category),
        "estimated_meals": estimate_meals(food_category, quantity_kg),
        "waste_risk": waste_risk_score(food_category, hours_elapsed),
        "hours_since_donation": round(hours_elapsed, 1),
    }


if __name__ == "__main__":
    # quick manual test
    result = score_donation("cooked_meals", 12.5, "2026-09-07T08:00:00")
    print(result)
