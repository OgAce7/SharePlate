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
        accepted_foods = str(ngo.get("food_types", "")).split("|")
        don_food = str(donation.get("food_type", "")).lower()

        # Flexible food type check
        if (
            don_food not in accepted_foods
            and "all" not in accepted_foods
            and don_food not in ["other", "snacks", "beverages"]
        ):
            # Allow fallback match if NGO accepts general meals or packaged food
            if not any(f in accepted_foods for f in ["cooked_meal", "packaged_food", "bakery_items"]):
                continue

        # Check pickup radius if defined
        dist = haversine_distance(
            float(donation.get("latitude", 26.9124)),
            float(donation.get("longitude", 75.7873)),
            float(ngo.get("latitude", 26.9124)),
            float(ngo.get("longitude", 75.7873)),
        )
        if "pickup_radius_km" in ngo and pd.notna(ngo["pickup_radius_km"]):
            if dist > float(ngo["pickup_radius_km"]) * 1.5:  # Soft radius threshold
                continue

        # Dietary compatibility
        if donation.get("vegan", 0) == 1 and ngo.get("vegan", 0) == 0:
            continue

        eligible_ngos.append(ngo)

    # NOTE: previously fell back to `return ngos.copy()` here when nothing
    # qualified, which silently ignored every filter above (food type,
    # radius, vegan) and matched the donation to *any* NGO -- including
    # ones that fail dietary/radius requirements -- with no way to tell.
    # It also meant pipeline.py's `if eligible.empty: unmatched_ids.append(...)`
    # could never trigger, so "no eligible NGO" was never actually reported.
    # Returning a real empty DataFrame here lets callers correctly treat
    # this donation as unmatched.
    if not eligible_ngos:
        return ngos.iloc[0:0].copy()

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

    ngos["distance_km"] = pd.to_numeric(ngos.get("distance_km", 0.0), errors="coerce").fillna(0.0)
    max_distance = ngos["distance_km"].max()

    if pd.isna(max_distance) or max_distance <= 0:
        ngos["distance_score"] = 1.0
    else:
        ngos["distance_score"] = 1.0 - (ngos["distance_km"] / max_distance)

    ngos["distance_score"] = ngos["distance_score"].fillna(1.0).clip(lower=0.0, upper=1.0)

    ngos["reliability_score"] = pd.to_numeric(
        ngos.get("reliability_score", 0.9),
        errors="coerce"
    ).fillna(0.9)

    ngos["final_score"] = (
        0.6 * ngos["distance_score"]
        + 0.4 * ngos["reliability_score"]
    ) * 100.0

    ngos["final_score"] = ngos["final_score"].fillna(85.0).round(1)

    return ngos