from __future__ import annotations
import requests

class ShareplateUnavailable(Exception):
    "The demand/food-intelligence service couldn't answer right now."


class ShareplateClient:
    def __init__(self, base_url: str = "http://localhost:8001", timeout: float = 0.2):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._offline_detected = False

    def _post(self, path: str, payload: dict) -> dict:
        if self._offline_detected:
            raise ShareplateUnavailable(f"{path}: service offline (cached)")
        try:
            resp = requests.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
            self._offline_detected = True
            raise ShareplateUnavailable(f"{path}: unreachable ({e})") from e

        if resp.status_code == 503:
            raise ShareplateUnavailable(f"{path}: service not ready ({resp.text})")
        if resp.status_code >= 500:
            raise ShareplateUnavailable(f"{path}: server error {resp.status_code} ({resp.text})")

        resp.raise_for_status()  
        return resp.json()

    def score_food(self, food_category: str, quantity_kg: float, donation_timestamp: str) -> dict:
        return self._post(
            "/score/food",
            {
                "food_category": food_category,
                "quantity_kg": quantity_kg,
                "donation_timestamp": donation_timestamp,
            },
        )

    def predict_demand(self, recipient_id: str, date: str) -> dict:
        if self._offline_detected:
            raise ShareplateUnavailable("/predict/demand: service offline (cached)")
        try:
            resp = requests.post(
                f"{self.base_url}/predict/demand",
                json={"recipient_id": recipient_id, "date": date},
                timeout=self.timeout,
            )
        except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
            self._offline_detected = True
            raise ShareplateUnavailable(f"/predict/demand: unreachable ({e})") from e

        if resp.status_code in (404, 503):
            raise ShareplateUnavailable(f"/predict/demand: {resp.status_code} ({resp.text})")
        if resp.status_code >= 500:
            raise ShareplateUnavailable(f"/predict/demand: server error {resp.status_code}")

        resp.raise_for_status()
        return resp.json()