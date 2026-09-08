from __future__ import annotations
import math
import os
import sys
from pathlib import Path
from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root and backend dir are in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.demand_intelligence import DemandIntelligenceEngine
from src.pipeline import build_matches
from src.register_donor import (
    DONOR_TYPES,
    FOOD_TYPES,
    ValidationError,
    register_donation,
)
from src.route_optimizer import default_fleet, optimize_routes, routes_to_dict

DATA_DIR = BASE_DIR / "data"
SHAREPLATE_API_URL = os.environ.get("SHAREPLATE_API_URL", "http://localhost:8001")

def _demand_engine() -> DemandIntelligenceEngine:
    return DemandIntelligenceEngine(shareplate_base_url=SHAREPLATE_API_URL)

def _safe_float(val, default: float = 0.0) -> float:
    import math
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return default

app = FastAPI(
    title="SharePlate API & Web Platform",
    description="AI-driven surplus food rescue and redistribution platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS)
if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Shared helper to load dataset
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    donations_path = DATA_DIR / "donations.csv"
    ngos_path = DATA_DIR / "ngos.csv"

    if not donations_path.exists() or not ngos_path.exists():
        raise HTTPException(
            status_code=500,
            detail="data/donations.csv or data/ngos.csv not found.",
        )

    donations = pd.read_csv(donations_path)
    ngos = pd.read_csv(ngos_path)
    donations.columns = donations.columns.str.strip()
    ngos.columns = ngos.columns.str.strip()
    return donations, ngos

# Request/Response Pydantic Models
class NewDonationRequest(BaseModel):
    food_type: str = Field(..., description=f"One of {FOOD_TYPES}")
    quantity: float = Field(..., gt=0)
    latitude: float
    longitude: float
    hours_until_expiry: float = Field(..., gt=0)
    unit: Optional[str] = Field(None, description="'meals' or 'kg'")
    perishability: Optional[str] = Field(None, description="'low' | 'medium' | 'high'")
    donor_type: str = Field("restaurant", description=f"One of {DONOR_TYPES}")
    vegetarian: int = Field(1, ge=0, le=1)
    vegan: int = Field(0, ge=0, le=1)
    pickup_required: int = Field(1, ge=0, le=1)
    strict_bounds: bool = Field(False)

class OptimizeRequest(BaseModel):
    num_trucks: int = Field(6, gt=0, le=50)
    truck_capacity_units: float = Field(250.0, gt=0)
    shift_minutes: int = Field(600, gt=0, le=1440)
    time_limit_seconds: int = Field(10, gt=0, le=60)
    max_donations: Optional[int] = Field(None)

# --- WEB DASHBOARD ROUTES ---

@app.get("/", response_class=HTMLResponse)
def serve_donor_dashboard():
    donor_file = BASE_DIR / "templates" / "donor.html"
    if donor_file.exists():
        return donor_file.read_text(encoding="utf-8")
    return "<h1>SharePlate Platform - Donor Dashboard Template Not Found</h1>"

@app.get("/donor", response_class=HTMLResponse)
def serve_donor_dashboard_alias():
    return serve_donor_dashboard()

@app.get("/ngo", response_class=HTMLResponse)
def serve_ngo_dashboard():
    ngo_file = BASE_DIR / "templates" / "ngo.html"
    if ngo_file.exists():
        return ngo_file.read_text(encoding="utf-8")
    return "<h1>SharePlate Platform - NGO Dashboard Template Not Found</h1>"


# --- API ENDPOINTS ---

@app.get("/health")
def health():
    return {"status": "ok", "service": "SharePlate Integrated Backend & Web Platform"}

def _clean_records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    clean_df = df.copy()
    for col in clean_df.columns:
        if pd.api.types.is_float_dtype(clean_df[col]) or pd.api.types.is_numeric_dtype(clean_df[col]):
            clean_df[col] = clean_df[col].apply(lambda x: 0.0 if (pd.isna(x) or math.isinf(float(x))) else float(x))
        else:
            clean_df[col] = clean_df[col].fillna("")
    return clean_df.to_dict(orient="records")

@app.get("/donations")
def get_donations(limit: Optional[int] = Query(None, gt=0)):
    donations, _ = _load_data()
    if isinstance(limit, int) and limit > 0:
        donations = donations.head(limit)
    return _clean_records(donations)

@app.get("/ngos")
def get_ngos():
    _, ngos = _load_data()
    engine = _demand_engine()
    scored = engine.score_ngo_demand(ngos)
    return _clean_records(scored)

def get_ai_ngo_matches(donation_row: dict, ngos_df: pd.DataFrame) -> list[dict]:
    if ngos_df.empty:
        return []
    
    don_series = pd.Series(donation_row)
    
    from src.matching_engine import find_eligible_ngos, add_distances, calculate_final_score
    
    eligible = find_eligible_ngos(don_series, ngos_df)
    if eligible.empty:
        # No NGO passes food-type/radius/dietary checks for this donation --
        # correctly return no candidates rather than silently offering an
        # incompatible NGO as the "AI top match" (see matching_engine.py).
        return []

    eligible = add_distances(don_series, eligible)
    eligible = calculate_final_score(don_series, eligible)
    eligible = eligible.sort_values("final_score", ascending=False)
    
    candidates = []
    for _, r in eligible.iterrows():
        dist = _safe_float(r.get("distance_km", 0.0), 0.0)
        match = _safe_float(r.get("final_score", 90.0), 90.0)
        rel = _safe_float(r.get("reliability_score", 0.9), 0.9)
        lat = _safe_float(r.get("latitude", 26.9124), 26.9124)
        lon = _safe_float(r.get("longitude", 75.7873), 75.7873)

        candidates.append({
            "ngo_id": str(r.get("ngo_id", "")),
            "ngo_name": str(r.get("ngo_name", "NGO Partner")),
            "distance_km": round(dist, 2),
            "match_score": round(match, 1),
            "reliability_score": round(rel, 2),
            "ngo_latitude": round(lat, 6),
            "ngo_longitude": round(lon, 6),
            "food_types": str(r.get("food_types", "")),
        })
    return candidates

@app.post("/donations")
@app.post("/donations/")
@app.post("/donor")
@app.post("/")
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
            pickup_required=payload.pickup_required,
            data_dir=DATA_DIR,
            strict_bounds=payload.strict_bounds,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    donations, ngos = _load_data()
    candidate_matches = get_ai_ngo_matches(row, ngos)
    best_match = candidate_matches[0] if candidate_matches else None

    return {
        "message": "Donation registered and matched successfully",
        "donation": row,
        "best_match": best_match,
        "candidate_matches": candidate_matches,
    }

@app.get("/donations/priority")
def donations_priority(limit: Optional[int] = Query(None, gt=0)):
    donations, _ = _load_data()
    engine = _demand_engine()
    scored = engine.score_donations(donations)
    if isinstance(limit, int) and limit > 0:
        scored = scored.head(limit)
    return _clean_records(scored)

@app.post("/match")
def match_donations(limit: Optional[int] = Query(None, gt=0)):
    donations, ngos = _load_data()
    if isinstance(limit, int) and limit > 0:
        donations = donations.head(limit)

    matches, unmatched = build_matches(donations, ngos)
    return {
        "matched_count": len(matches),
        "unmatched_count": len(unmatched),
        "unmatched_donation_ids": unmatched,
        "matches": _clean_records(matches),
    }

@app.post("/donations/{donation_id}/claim")
def claim_donation(donation_id: str):
    donations_path = DATA_DIR / "donations.csv"
    if not donations_path.exists():
        raise HTTPException(status_code=404, detail="donations.csv not found")

    donations_df = pd.read_csv(donations_path)
    donations_df.columns = donations_df.columns.str.strip()

    if donation_id in donations_df["donation_id"].values:
        # Remove claimed donation from available listings
        donations_df = donations_df[donations_df["donation_id"] != donation_id]
        donations_df.to_csv(donations_path, index=False)
        return {"status": "claimed", "donation_id": donation_id, "message": "Donation claimed successfully"}
    
    return {"status": "claimed", "donation_id": donation_id, "message": "Donation recorded as claimed"}

class UpdateTrackingRequest(BaseModel):
    status: str

# Safety Evaluation Helper
def get_safety_status(hours_until_expiry: float) -> str:
    if hours_until_expiry <= 0:
        return "EXPIRED"
    elif hours_until_expiry <= 3:
        return "CRITICAL"
    elif hours_until_expiry <= 6:
        return "WARNING"
    else:
        return "SAFE"

TRACKING_STATUSES = ["PENDING", "ASSIGNED", "PICKED_UP", "IN_TRANSIT", "DELIVERED"]

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

# --- SAFETY, TRACKING & ANALYTICS ENDPOINTS ---

@app.get("/api/safety/check")
def safety_check(hours_until_expiry: float, donation_id: Optional[str] = None):
    status = get_safety_status(hours_until_expiry)
    messages = {
        "EXPIRED": "Food has expired. Do not distribute.",
        "CRITICAL": "Food is critically close to expiry.",
        "WARNING": "Food is approaching expiry.",
        "SAFE": "Food is currently safe."
    }
    return {
        "donation_id": donation_id,
        "hours_until_expiry": hours_until_expiry,
        "status": status,
        "message": messages.get(status, "Food status checked.")
    }

@app.get("/api/safety/{donation_id}")
def get_donation_safety(donation_id: str):
    donations, _ = _load_data()
    row = donations[donations["donation_id"] == donation_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Donation not found")
    
    hours = float(row.iloc[0]["hours_until_expiry"])
    food_type = str(row.iloc[0]["food_type"])
    status = get_safety_status(hours)
    messages = {
        "EXPIRED": "Food has expired. Do not distribute.",
        "CRITICAL": "Food is critically close to expiry.",
        "WARNING": "Food is approaching expiry.",
        "SAFE": "Food is currently safe."
    }
    return {
        "donation_id": donation_id,
        "food_type": food_type,
        "hours_until_expiry": hours,
        "status": status,
        "message": messages.get(status, "Food status checked.")
    }

@app.get("/api/tracking/{donation_id}")
def get_tracking(donation_id: str):
    donations, _ = _load_data()
    row = donations[donations["donation_id"] == donation_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Donation not found")
    
    tracking_status = row.iloc[0].get("tracking_status", "PENDING")
    if pd.isna(tracking_status):
        tracking_status = "PENDING"
    return {
        "donation_id": donation_id,
        "tracking_status": tracking_status
    }

@app.put("/api/tracking/{donation_id}")
def update_tracking(donation_id: str, payload: UpdateTrackingRequest):
    new_status = payload.status.upper()
    if new_status not in TRACKING_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid tracking status. Allowed: {TRACKING_STATUSES}")
    
    donations_path = DATA_DIR / "donations.csv"
    if not donations_path.exists():
        raise HTTPException(status_code=404, detail="donations.csv not found")
    
    donations_df = pd.read_csv(donations_path)
    donations_df.columns = donations_df.columns.str.strip()
    
    if "tracking_status" not in donations_df.columns:
        donations_df["tracking_status"] = "PENDING"
        
    mask = donations_df["donation_id"] == donation_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Donation not found")
        
    current_status = donations_df.loc[mask, "tracking_status"].values[0]
    if pd.isna(current_status):
        current_status = "PENDING"
        
    curr_idx = TRACKING_STATUSES.index(current_status) if current_status in TRACKING_STATUSES else 0
    new_idx = TRACKING_STATUSES.index(new_status)
    
    if new_idx != curr_idx + 1 and new_idx != curr_idx:
        next_allowed = TRACKING_STATUSES[curr_idx + 1] if curr_idx + 1 < len(TRACKING_STATUSES) else None
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status progression from {current_status}. Next allowed status: {next_allowed}"
        )
        
    donations_df.loc[mask, "tracking_status"] = new_status
    donations_df.to_csv(donations_path, index=False)
    
    return {
        "donation_id": donation_id,
        "tracking_status": new_status,
        "message": "Tracking status updated successfully"
    }

@app.get("/api/analytics/summary")
def analytics_summary():
    donations, _ = _load_data()
    total_donations = len(donations)
    total_quantity = float(donations["quantity"].sum()) if not donations.empty else 0.0
    
    safety_counts = {"safe": 0, "warning": 0, "critical": 0, "expired": 0}
    tracking_counts = {"pending": 0, "assigned": 0, "picked_up": 0, "in_transit": 0, "delivered": 0}
    
    if not donations.empty:
        for _, row in donations.iterrows():
            hours = float(row.get("hours_until_expiry", 12))
            st = get_safety_status(hours).lower()
            if st in safety_counts:
                safety_counts[st] += 1
                
            tr = str(row.get("tracking_status", "PENDING")).lower()
            if tr in tracking_counts:
                tracking_counts[tr] += 1
            else:
                tracking_counts["pending"] += 1
                
    return {
        "total_donations": total_donations,
        "total_quantity": total_quantity,
        "safety": safety_counts,
        "tracking": tracking_counts
    }

@app.get("/api/analytics/food-types")
def analytics_food_types():
    donations, _ = _load_data()
    if donations.empty:
        return []
    
    grouped = donations.groupby("food_type").agg(
        donation_count=("donation_id", "count"),
        total_quantity=("quantity", "sum")
    ).reset_index()
    return _clean_records(grouped)

@app.get("/api/analytics/tracking")
def analytics_tracking():
    donations, _ = _load_data()
    result = []
    for st in TRACKING_STATUSES:
        if "tracking_status" in donations.columns:
            count = int((donations["tracking_status"] == st).sum())
        else:
            count = len(donations) if st == "PENDING" else 0
        result.append({"status": st, "count": count})
    return result

@app.get("/api/analytics/safety")
def analytics_safety():
    donations, _ = _load_data()
    statuses = ["SAFE", "WARNING", "CRITICAL", "EXPIRED"]
    counts = {st: 0 for st in statuses}
    if not donations.empty:
        for _, row in donations.iterrows():
            hours = float(row.get("hours_until_expiry", 12))
            st = get_safety_status(hours)
            counts[st] += 1
    return [{"status": st, "count": counts[st]} for st in statuses]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)