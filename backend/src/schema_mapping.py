from __future__ import annotations
from datetime import datetime, timedelta

# Food categories
FOOD_TYPE_TO_CATEGORY: dict[str, str] = {
    "cooked_meal": "cooked_meals",       
    "fruits": "fruits",
    "vegetables": "vegetables",
    "bakery": "bakery",
    "packaged_food": "packaged_snacks",  
}

DEFAULT_CATEGORY = "bakery"  

def to_food_category(food_type: str) -> str:
    return FOOD_TYPE_TO_CATEGORY.get(food_type, DEFAULT_CATEGORY)

# Quantity units
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

def quantity_to_kg(quantity: float, unit: str, food_category: str) -> float:
    if unit == "kg":
        return float(quantity)
    factor = MEALS_PER_KG.get(food_category, 2.5)
    if factor <= 0:
        return float(quantity)
    return float(quantity) / factor

# 3. hours until expiry
def estimate_donation_timestamp(
    hours_until_expiry: float, food_category: str, now: datetime | None = None
) -> str:
    now = now or datetime.utcnow()
    shelf_life_hours = SHELF_LIFE_DAYS.get(food_category, 3) * 24
    hours_since_donation = max(0.0, shelf_life_hours - float(hours_until_expiry))
    donated_at = now - timedelta(hours=hours_since_donation)
    return donated_at.isoformat()