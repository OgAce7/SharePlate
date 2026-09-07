import math
import pandas as pd

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def find_eligible_ngos(donation, ngos):
    eligible_ngos = []

    for _, ngo in ngos.iterrows():

        accepted_foods = str(ngo["food_types"]).split("|")

        # Checking food type
        if donation["food_type"] not in accepted_foods:
            continue

        # Check remaining capacity
        if donation["unit"] == "meals":
            remaining = ngo["max_capacity_meals"] - ngo.get("current_demand_meals", 0)
            if donation["quantity"] > remaining:
                continue

        elif donation["unit"] == "kg":
            remaining = ngo["max_capacity_kg"] - ngo.get("current_demand_kg", 0)
            if donation["quantity"] > remaining:
                continue

        else:
            continue

        # Check pickup radius
        dist = haversine_distance(
            donation["latitude"], donation["longitude"],
            ngo["latitude"], ngo["longitude"],
        )
        if "pickup_radius_km" in ngo and dist > ngo["pickup_radius_km"]:
            continue

        # Check khane ki compatibility
        if donation.get("vegan", 0) == 1 and ngo.get("vegan", 0) == 0:
            continue
        if donation.get("vegetarian", 0) == 1 and ngo.get("vegetarian", 0) == 0:
            continue

        eligible_ngos.append(ngo)

    return pd.DataFrame(eligible_ngos)

def add_distances(donation, ngos):

    if ngos.empty:
        return ngos.copy()

    ngos = ngos.copy()

    ngos["distance_km"] = ngos.apply(
        lambda ngo: haversine_distance(
            donation["latitude"],
            donation["longitude"],
            ngo["latitude"],
            ngo["longitude"]
        ),
        axis=1
    )

    return ngos

def calculate_final_score(donation, ngos):

    if ngos.empty:
        return ngos.copy()

    ngos = ngos.copy()

    max_distance = ngos["distance_km"].max()

    if max_distance == 0:
        ngos["distance_score"] = 1
    else:
        ngos["distance_score"] = 1 - (
            ngos["distance_km"] / max_distance
        )

    ngos["reliability_score"] = pd.to_numeric(
        ngos["reliability_score"],
        errors="coerce"
    ).fillna(0)

    ngos["final_score"] = (
        0.6 * ngos["distance_score"]
        + 0.4 * ngos["reliability_score"]
    ) * 100

    return ngos