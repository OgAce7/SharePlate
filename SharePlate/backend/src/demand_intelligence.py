from __future__ import annotations
import math
from datetime import date as date_cls
import pandas as pd
from .schema_mapping import estimate_donation_timestamp, quantity_to_kg, to_food_category
from .shareplate_client import ShareplateClient, ShareplateUnavailable

# Local heuristic incase XgBoost dies
PERISHABILITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.25}
CRITICAL_HOURS_THRESHOLD = 3.0

def _local_urgency_score(hours_until_expiry: float, perishability: str) -> float:
    weight = PERISHABILITY_WEIGHT.get(str(perishability).lower(), 0.5)
    decay = math.exp(-hours_until_expiry / (12.0 / max(weight, 0.05)))
    score = 100 * decay
    if hours_until_expiry <= CRITICAL_HOURS_THRESHOLD:
        score = max(score, 90.0)
    return round(min(score, 100.0), 2)

def _spoilage_risk_label(urgency_score: float) -> str:
    if urgency_score >= 75:
        return "high"
    elif urgency_score >= 40:
        return "medium"
    return "low"

class DemandIntelligenceEngine:
    def __init__(
        self,
        use_ml: bool = False,  
        shareplate_base_url: str = "http://localhost:8001",
        timeout: float = 3.0,
    ):
        self.client = ShareplateClient(base_url=shareplate_base_url, timeout=timeout)

    def score_donations(self, donations: pd.DataFrame) -> pd.DataFrame:
        df = donations.copy()

        urgency_scores = []
        sources = []
        estimated_meals = []

        for _, row in df.iterrows():
            hours_until_expiry = float(row["hours_until_expiry"])
            perishability = row.get("perishability", "medium")
            food_type = row["food_type"]
            category = to_food_category(food_type)

            try:
                quantity_kg = quantity_to_kg(row["quantity"], row["unit"], category)
                donation_ts = estimate_donation_timestamp(hours_until_expiry, category)
                result = self.client.score_food(category, quantity_kg, donation_ts)

                urgency_scores.append(round(result["waste_risk"] * 100, 2))
                estimated_meals.append(result.get("estimated_meals"))
                sources.append("shareplate_api")
            except Exception:
                urgency_scores.append(_local_urgency_score(hours_until_expiry, perishability))
                estimated_meals.append(None)
                sources.append("local_fallback")

        df["urgency_score"] = urgency_scores
        df["urgency_source"] = sources
        df["estimated_meals"] = estimated_meals
        df["spoilage_risk"] = df["urgency_score"].apply(_spoilage_risk_label)
        df["priority_rank"] = df["urgency_score"].rank(ascending=False, method="first").astype(int)

        return df.sort_values("priority_rank").reset_index(drop=True)

    def score_ngo_demand(self, ngos: pd.DataFrame) -> pd.DataFrame:
        df = ngos.copy()
        today = date_cls.today().isoformat()

        def _pressure(current, maximum):
            if not maximum or maximum <= 0:
                return 0.0
            return round(min(current / maximum, 1.0), 3)

        df["demand_pressure_meals"] = df.apply(
            lambda r: _pressure(r.get("current_demand_meals", 0), r.get("max_capacity_meals", 0)),
            axis=1,
        )
        df["demand_pressure_kg"] = df.apply(
            lambda r: _pressure(r.get("current_demand_kg", 0), r.get("max_capacity_kg", 0)),
            axis=1,
        )

        predicted_kg = []
        demand_sources = []
        for _, row in df.iterrows():
            try:
                result = self.client.predict_demand(row["ngo_id"], today)
                predicted_kg.append(result["predicted_quantity_kg"])
                demand_sources.append("shareplate_api")
            except Exception:
                predicted_kg.append(None)
                demand_sources.append("local_fallback")

        df["predicted_demand_kg"] = predicted_kg
        df["demand_source"] = demand_sources
        base = (
            0.7 * df[["demand_pressure_meals", "demand_pressure_kg"]].max(axis=1)
            + 0.3 * pd.to_numeric(df.get("reliability_score", 0), errors="coerce").fillna(0)
        ) * 100

        def _predicted_bump(row):
            if row["predicted_demand_kg"] is None:
                return 0.0
            cap = row.get("max_capacity_kg", 0) or 0
            if cap <= 0:
                return 0.0
            return min(row["predicted_demand_kg"] / cap, 1.0) * 10

        df["need_score"] = (base + df.apply(_predicted_bump, axis=1)).round(2)

        return df
    def _predict_urgency_ml(self, donations: pd.DataFrame) -> pd.Series:
        raise NotImplementedError("Superseded by ShareplateClient.score_food")

    def _predict_demand_ml(self, ngos: pd.DataFrame) -> pd.Series:
        raise NotImplementedError("Superseded by ShareplateClient.predict_demand")