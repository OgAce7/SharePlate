"""
train_model.py

Loads demand.csv, engineers features, trains a baseline
RandomForest model, then compares against XGBoost.
Saves the best model to models/demand_model.pkl
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor


def load_data():
    df = pd.read_csv("data/demand.csv", parse_dates=["date"])
    df = df.sort_values(["recipient_id", "date"]).reset_index(drop=True)
    return df



def engineer_features(df):
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = df["date"].dt.month
    df["day_of_month"] = df["date"].dt.day

    
    df["rolling_7"] = (
        df.groupby("recipient_id")["quantity_needed_kg"]
        .transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    )
    df["rolling_30"] = (
        df.groupby("recipient_id")["quantity_needed_kg"]
        .transform(lambda s: s.shift(1).rolling(30, min_periods=1).mean())
    )

    
    df["rolling_7"] = df["rolling_7"].fillna(df.groupby("recipient_id")["quantity_needed_kg"].transform("mean"))
    df["rolling_30"] = df["rolling_30"].fillna(df.groupby("recipient_id")["quantity_needed_kg"].transform("mean"))

    le = LabelEncoder()
    df["recipient_size_enc"] = le.fit_transform(df["recipient_size"])

    return df, le



def split_data(df, test_days=30):
    cutoff = df["date"].max() - pd.Timedelta(days=test_days)
    train = df[df["date"] <= cutoff]
    test = df[df["date"] > cutoff]
    return train, test


FEATURES = [
    "day_of_week", "is_weekend", "month", "day_of_month",
    "rolling_7", "rolling_30", "recipient_size_enc",
]
TARGET = "quantity_needed_kg"



def evaluate(model, X_test, y_test, name):
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"{name:15s} MAE: {mae:6.2f}   RMSE: {rmse:6.2f}")
    return mae


if __name__ == "__main__":
    df = load_data()
    df, size_encoder = engineer_features(df)
    train, test = split_data(df)

    X_train, y_train = train[FEATURES], train[TARGET]
    X_test, y_test = test[FEATURES], test[TARGET]

    rf = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    rf.fit(X_train, y_train)
    rf_mae = evaluate(rf, X_test, y_test, "RandomForest")

    xgb = XGBRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42
    )
    xgb.fit(X_train, y_train)
    xgb_mae = evaluate(xgb, X_test, y_test, "XGBoost")

    best_model, best_name = (xgb, "xgboost") if xgb_mae < rf_mae else (rf, "random_forest")
    print(f"\nBest model: {best_name}")

    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model, "models/demand_model.pkl")
    joblib.dump(size_encoder, "models/size_encoder.pkl")
    joblib.dump(FEATURES, "models/feature_list.pkl")
    print("Saved model -> models/demand_model.pkl")
