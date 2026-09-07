from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.demand_intelligence import DemandIntelligenceEngine
from src.pipeline import build_matches
from src.register_donor import (
    DONOR_TYPES,
    FOOD_TYPES,
    ValidationError,
    register_donation,
)
from src.route_optimizer import default_fleet, optimize_routes, routes_to_dict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SHAREPLATE_API_URL = os.environ.get("SHAREPLATE_API_URL", "http://localhost:8001")

def _demand_engine() -> DemandIntelligenceEngine:
    return DemandIntelligenceEngine(shareplate_base_url=SHAREPLATE_API_URL)

app = FastAPI(
    title="SharePlate API",
    description="AI-driven surplus food rescue and redistribution backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared helpers (nalle log)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    donations_path = DATA_DIR / "donations.csv"
    ngos_path = DATA_DIR / "ngos.csv"

    if not donations_path.exists() or not ngos_path.exists():
        raise HTTPException(
            status_code=500,
            detail="data/donations.csv or data/ngos.csv not found. "
            "Run `python -m src.generate_synthetic_data` first.",
        )

    donations = pd.read_csv(donations_path)
    ngos = pd.read_csv(ngos_path)
    donations.columns = donations.columns.str.strip()
    ngos.columns = ngos.columns.str.strip()
    return donations, ngos

# Req/response model
class NewDonationRequest(BaseModel):
    food_type: str = Field(..., description=f"One of {FOOD_TYPES}")
    quantity: float = Field(..., gt=0)
    latitude: float
    longitude: float
    hours_until_expiry: float = Field(..., gt=0)
    unit: Optional[str] = Field(None, description="'meals' or 'kg'; inferred from food_type if omitted")
    perishability: Optional[str] = Field(None, description="'low' | 'medium' | 'high'; inferred if omitted")
    donor_type: str = Field("restaurant", description=f"One of {DONOR_TYPES}")
    vegetarian: int = Field(1, ge=0, le=1)
    vegan: int = Field(0, ge=0, le=1)
    strict_bounds: bool = Field(False, description="Reject coordinates outside the expected service area")

class OptimizeRequest(BaseModel):
    num_trucks: int = Field(6, gt=0, le=50)
    truck_capacity_units: float = Field(250.0, gt=0)
    shift_minutes: int = Field(600, gt=0, le=1440)
    time_limit_seconds: int = Field(10, gt=0, le=60)
    max_donations: Optional[int] = Field(
        None, description="Optional cap on how many (most urgent) donations to process, for faster demo runs"
    )

# Routes
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/donations")
def get_donations(limit: Optional[int] = Query(None, gt=0)):
    donations, _ = _load_data()
    if limit:
        donations = donations.head(limit)
    return donations.to_dict(orient="records")

@app.get("/ngos")
def get_ngos():
    _, ngos = _load_data()
    engine = _demand_engine()
    scored = engine.score_ngo_demand(ngos)
    return scored.to_dict(orient="records")

@app.post("/donations")
def create_donation(payload: NewDonationRequest):
    try:
        row = register_donation(
            food_type=payload.food_type,
            quantity=payload.quantity,
            lat=payload.latitude,
            lon=payload.longitude,
            hours_until_expiry=payload.hours_until_expiry,
            unit=payload.unit,
            perishability=payload.perishability,
            donor_type=payload.donor_type,
            vegetarian=payload.vegetarian,
            vegan=payload.vegan,
            data_dir=DATA_DIR,
            strict_bounds=payload.strict_bounds,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"message": "Donation registered", "donation": row}

@app.get("/donations/priority")
def donations_priority(limit: Optional[int] = Query(None, gt=0)):
    donations, _ = _load_data()
    engine = _demand_engine()
    scored = engine.score_donations(donations)
    if limit:
        scored = scored.head(limit)
    return scored.to_dict(orient="records")

@app.post("/match")
def match_donations(limit: Optional[int] = Query(None, gt=0)):
    donations, ngos = _load_data()
    if limit:
        donations = donations.head(limit)

    matches, unmatched = build_matches(donations, ngos)
    return {
        "matched_count": len(matches),
        "unmatched_count": len(unmatched),
        "unmatched_donation_ids": unmatched,
        "matches": matches.to_dict(orient="records"),
    }

@app.post("/routes/optimize")
def optimize(payload: OptimizeRequest):
    donations, ngos = _load_data()
    if payload.max_donations:
        donations = donations.head(payload.max_donations)

    matches, unmatched_match = build_matches(donations, ngos)

    if matches.empty:
        return {
            "routes": [],
            "unassigned_donation_ids": [],
            "unmatched_donation_ids": unmatched_match,
            "message": "No donations could be matched to an eligible NGO.",
        }

    fleet = default_fleet(
        num_trucks=payload.num_trucks,
        capacity_units=payload.truck_capacity_units,
        shift_minutes=payload.shift_minutes,
    )

    result = optimize_routes(matches, fleet=fleet, time_limit_seconds=payload.time_limit_seconds)
    result_dict = routes_to_dict(result)
    result_dict["unmatched_donation_ids"] = unmatched_match
    result_dict["matched_count"] = len(matches)

    return result_dict

@app.post("/data/regenerate")
def regenerate_data(donations: int = Query(300, gt=0, le=5000), ngos: int = Query(40, gt=0, le=500)):
    from src.generate_synthetic_data import generate_donations, generate_ngos

    donations_df = generate_donations(n=donations)
    ngos_df = generate_ngos(n=ngos)

    donations_df.to_csv(DATA_DIR / "donations.csv", index=False)
    ngos_df.to_csv(DATA_DIR / "ngos.csv", index=False)

    return {"donations_written": len(donations_df), "ngos_written": len(ngos_df)}