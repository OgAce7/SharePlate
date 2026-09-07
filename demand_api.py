"""
demand_api.py

FastAPI app exposing:
    POST /predict/demand   -> forecasted quantity for a recipient/date
    POST /score/food       -> shelf life, meals estimate, waste risk

Run with: uvicorn demand_api:app --reload
Docs at:  http://127.0.0.1:8000/docs
"""

from datetime import datetime

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from food_intelligence import score_donation

app = FastAPI(title="Demand + Food Intelligence Service")

# ---------- load model artifacts once at startup ----------
try:
    demand_model = joblib.load("models/demand_model.pkl")
    size_encoder = joblib.load("models/size_encoder.pkl")
    feature_list = joblib.load("models/feature_list.pkl")
except FileNotFoundError:
    demand_model = None
    size_encoder = None
    feature_list = None

# recipient lookup (size), loaded from the same synthetic data
try:
    recipients_df = pd.read_csv("data/recipients.csv").set_index("recipient_id")
except FileNotFoundError:
    recipients_df = None

# historical demand, used to compute each recipient's real recent averages
try:
    demand_history_df = pd.read_csv("data/demand.csv", parse_dates=["date"])
except FileNotFoundError:
    demand_history_df = None


def get_recent_averages(recipient_id: str, as_of_date: pd.Timestamp) -> tuple[float, float]:
    """
    Returns (rolling_7, rolling_30): the recipient's average demand over the
    7 and 30 days strictly before as_of_date. Falls back to the recipient's
    overall historical mean if there isn't enough recent history, and to a
    flat default only if the recipient has no history at all.
    """
    DEFAULT_QUANTITY = 50.0

    if demand_history_df is None:
        return DEFAULT_QUANTITY, DEFAULT_QUANTITY

    recipient_history = demand_history_df[
        (demand_history_df["recipient_id"] == recipient_id)
        & (demand_history_df["date"] < as_of_date)
    ]

    if recipient_history.empty:
        return DEFAULT_QUANTITY, DEFAULT_QUANTITY

    overall_mean = recipient_history["quantity_needed_kg"].mean()

    last_7 = recipient_history[recipient_history["date"] >= as_of_date - pd.Timedelta(days=7)]
    last_30 = recipient_history[recipient_history["date"] >= as_of_date - pd.Timedelta(days=30)]

    rolling_7 = last_7["quantity_needed_kg"].mean() if not last_7.empty else overall_mean
    rolling_30 = last_30["quantity_needed_kg"].mean() if not last_30.empty else overall_mean

    return float(rolling_7), float(rolling_30)


# ---------- request/response schemas ----------
class DemandRequest(BaseModel):
    recipient_id: str
    date: str  # 'YYYY-MM-DD'


class DemandResponse(BaseModel):
    recipient_id: str
    date: str
    predicted_quantity_kg: float


class FoodScoreRequest(BaseModel):
    food_category: str
    quantity_kg: float
    donation_timestamp: str  # ISO format


@app.get("/")
def health_check():
    return {"status": "ok", "model_loaded": demand_model is not None}


@app.post("/predict/demand", response_model=DemandResponse)
def predict_demand(req: DemandRequest):
    if demand_model is None:
        raise HTTPException(status_code=503, detail="Model not trained yet. Run train_model.py first.")

    if recipients_df is None or req.recipient_id not in recipients_df.index:
        raise HTTPException(status_code=404, detail=f"Unknown recipient_id: {req.recipient_id}")

    date = pd.to_datetime(req.date)
    size = recipients_df.loc[req.recipient_id, "size"]
    size_enc = size_encoder.transform([size])[0]

    rolling_7, rolling_30 = get_recent_averages(req.recipient_id, date)

    features = pd.DataFrame([{
        "day_of_week": date.dayofweek,
        "is_weekend": int(date.dayofweek >= 5),
        "month": date.month,
        "day_of_month": date.day,
        "rolling_7": rolling_7,
        "rolling_30": rolling_30,
        "recipient_size_enc": size_enc,
    }])[feature_list]

    prediction = float(demand_model.predict(features)[0])

    return DemandResponse(
        recipient_id=req.recipient_id,
        date=req.date,
        predicted_quantity_kg=round(prediction, 1),
    )


@app.post("/score/food")
def score_food(req: FoodScoreRequest):
    try:
        return score_donation(req.food_category, req.quantity_kg, req.donation_timestamp)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))