from __future__ import annotations
import os
import pandas as pd
from .demand_intelligence import DemandIntelligenceEngine
from .matching_engine import add_distances, calculate_final_score, find_eligible_ngos

SHAREPLATE_API_URL = os.environ.get("SHAREPLATE_API_URL", "http://localhost:8001")

def build_matches(donations: pd.DataFrame, ngos: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    engine = DemandIntelligenceEngine(shareplate_base_url=SHAREPLATE_API_URL)
    scored_donations = engine.score_donations(donations)

    ngos_working = ngos.copy()
    ngos_working["current_demand_meals"] = pd.to_numeric(
        ngos_working.get("current_demand_meals", 0), errors="coerce"
    ).fillna(0)
    ngos_working["current_demand_kg"] = pd.to_numeric(
        ngos_working.get("current_demand_kg", 0), errors="coerce"
    ).fillna(0)

    matched_rows = []
    unmatched_ids: list[str] = []

    for _, donation in scored_donations.iterrows():
        eligible = find_eligible_ngos(donation, ngos_working)

        if eligible.empty:
            unmatched_ids.append(donation["donation_id"])
            continue

        eligible = add_distances(donation, eligible)
        eligible = calculate_final_score(donation, eligible)
        best = eligible.sort_values("final_score", ascending=False).iloc[0]

        matched_rows.append({
            "donation_id": donation["donation_id"],
            "food_type": donation["food_type"],
            "quantity": donation["quantity"],
            "unit": donation["unit"],
            "latitude": donation["latitude"],
            "longitude": donation["longitude"],
            "hours_until_expiry": donation["hours_until_expiry"],
            "urgency_score": donation["urgency_score"],
            "urgency_source": donation.get("urgency_source", "unknown"),
            "ngo_id": best["ngo_id"],
            "ngo_name": best["ngo_name"],
            "ngo_latitude": best["latitude"],
            "ngo_longitude": best["longitude"],
            "match_score": round(float(best["final_score"]), 2),
        })
        mask = ngos_working["ngo_id"] == best["ngo_id"]
        if donation["unit"] == "meals":
            ngos_working.loc[mask, "current_demand_meals"] += donation["quantity"]
        else:
            ngos_working.loc[mask, "current_demand_kg"] += donation["quantity"]

    matches_df = pd.DataFrame(matched_rows)
    return matches_df, unmatched_ids