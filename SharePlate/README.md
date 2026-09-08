# Demand + Food Intelligence Module

Predicts recipient food demand and scores individual donations (shelf life,
meal estimate, waste risk). Built for integration with the AI Matching
Engine (Module 1).

## Stack
Python, Pandas, NumPy, scikit-learn, XGBoost, FastAPI

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install pandas numpy scikit-learn xgboost fastapi uvicorn faker joblib
```

Mac users may also need:
```bash
brew install libomp
```
(required for XGBoost to load)

## Running

```bash
python generate_data.py        # creates data/*.csv (synthetic demand + donation history)
python train_model.py          # trains + saves the demand model to models/
uvicorn demand_api:app --reload  # starts the API on http://127.0.0.1:8000
```

Interactive docs: `http://127.0.0.1:8000/docs`

---

## API Reference

### `POST /predict/demand`

Predicts how much food (kg) a recipient will need on a given date, based on
their historical demand pattern (day-of-week trends, recent 7/30-day
averages, recipient size).

**Request**
```json
{
  "recipient_id": "R001",
  "date": "2026-09-10"
}
```

**Response**
```json
{
  "recipient_id": "R001",
  "date": "2026-09-10",
  "predicted_quantity_kg": 22.4
}
```

**Errors**
- `404` — unknown `recipient_id`
- `503` — model not trained yet (run `train_model.py` first)

---

### `POST /score/food`

Scores a single donation: shelf life, estimated number of meals it produces,
and a waste-risk score (0–1, higher = more urgent to match before it
spoils).

**Request**
```json
{
  "food_category": "cooked_meals",
  "quantity_kg": 12.5,
  "donation_timestamp": "2026-09-07T08:00:00"
}
```

`food_category` options: `cooked_meals`, `rice_grains`, `vegetables`,
`fruits`, `bakery`, `dairy`, `packaged_snacks`, `beverages`

**Response**
```json
{
  "food_category": "cooked_meals",
  "quantity_kg": 12.5,
  "shelf_life_days": 1,
  "estimated_meals": 31.2,
  "waste_risk": 0.26,
  "hours_since_donation": 6.2
}
```

**Errors**
- `400` — invalid `donation_timestamp` format (must be ISO 8601)

---

### `GET /`

Health check.

**Response**
```json
{
  "status": "ok",
  "model_loaded": true
}
```

---

## Notes for Module 1 (Matching Engine) integration

- Call `/score/food` right when a donation comes in, to get its waste-risk
  score — high-risk donations should be prioritized in matching.
- Call `/predict/demand` per recipient to help rank which recipient needs
  that donation most.
- Currently running on synthetic data (`generate_data.py`). Once real
  donation/demand data is available in the shared PostgreSQL database
  (Module 4), swap the CSV reads in `demand_api.py` for DB queries — the
  endpoint contracts (request/response shape) won't need to change.
- Base URL for local dev: `http://127.0.0.1:8000`. Update this once deployed.

## Files

| File | Purpose |
|---|---|
| `generate_data.py` | Generates synthetic donation + demand history |
| `train_model.py` | Feature engineering + model training (RandomForest / XGBoost) |
| `food_intelligence.py` | Shelf life, meals estimate, waste risk logic |
| `demand_api.py` | FastAPI app exposing both endpoints |
