"""
main.py

FastAPI app exposing:
    POST /predict/demand   -> forecasted quantity for a recipient/date
    POST /score/food       -> shelf life, meals estimate, waste risk

Run with: uvicorn main:app --reload
Docs at:  http://127.0.0.1:8000/docs
"""

from datetime import datetime

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from food_intelligence import score_donation

app = FastAPI(title="Demand + Food Intelligence Service")


try:
    demand_model = joblib.load("models/demand_model.pkl")
    size_encoder = joblib.load("models/size_encoder.pkl")
    feature_list = joblib.load("models/feature_list.pkl")
except FileNotFoundError:
    demand_model = None
    size_encoder = None
    feature_list = None


try:
    recipients_df = pd.read_csv("data/recipients.csv").set_index("recipient_id")
except FileNotFoundError:
    recipients_df = None



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

    
    features = pd.DataFrame([{
        "day_of_week": date.dayofweek,
        "is_weekend": int(date.dayofweek >= 5),
        "month": date.month,
        "day_of_month": date.day,
        "rolling_7": 50.0,
        "rolling_30": 50.0,
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
