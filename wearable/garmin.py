"""Garmin Connect API adapter with real API integration.

Uses Garmin Health API for fitness and health data.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from wearable.base_adapter import BaseWearableAdapter, NormalizedBiosignals

logger = logging.getLogger(__name__)
TOKEN_FILE = Path.home() / ".phta" / "garmin_token.json"
GARMIN_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/token"
GARMIN_API_BASE = "https://connectapi.garmin.com"


class GarminAdapter(BaseWearableAdapter):
    def __init__(self) -> None:
        self._client_id = os.environ.get("GARMIN_CLIENT_ID", "")
        self._access_token: str | None = None
        self._token_secret: str | None = None
        self._load_token()

    def _load_token(self) -> None:
        if not TOKEN_FILE.exists():
            return
        try:
            data = json.loads(TOKEN_FILE.read_text())
            self._access_token = data.get("access_token")
            self._token_secret = data.get("token_secret")
        except Exception:
            pass

    def _save_token(self) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps({
            "access_token": self._access_token,
            "token_secret": self._token_secret,
        }))

    async def authenticate(self) -> bool:
        return bool(self._client_id and self._access_token)

    async def fetch_recent_data(self) -> NormalizedBiosignals:
        if not self._access_token:
            return NormalizedBiosignals(device_source="garmin")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        result = NormalizedBiosignals(device_source="garmin", timestamp=datetime.now(timezone.utc))
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                hr_resp = await client.get(f"{GARMIN_API_BASE}/wellness-api/rest/health/heartRate?date={date_str}", headers=headers)
                if hr_resp.status_code == 200:
                    hr_data = hr_resp.json()
                    result.heart_rate_bpm = hr_data.get("currentHeartRate")
                    result.heart_rate_resting = hr_data.get("restingHeartRate")

                stress_resp = await client.get(f"{GARMIN_API_BASE}/wellness-api/rest/health/stress?date={date_str}", headers=headers)
                if stress_resp.status_code == 200:
                    stress_data = stress_resp.json()
                    result.stress_score = stress_data.get("overallStressLevel")

                steps_resp = await client.get(f"{GARMIN_API_BASE}/wellness-api/rest/health/steps?date={date_str}", headers=headers)
                if steps_resp.status_code == 200:
                    steps_data = steps_resp.json()
                    result.steps_today = steps_data.get("totalSteps")

                spo2_resp = await client.get(f"{GARMIN_API_BASE}/wellness-api/rest/health/spo2?date={date_str}", headers=headers)
                if spo2_resp.status_code == 200:
                    spo2_data = spo2_resp.json()
                    avg_spo2 = spo2_data.get("averageSpO2")
                    if avg_spo2:
                        result.spo2_percent = float(avg_spo2)

            result.data_freshness_minutes = 10
        except Exception:
            logger.exception("Garmin data fetch failed")
        return result

    def is_available(self) -> bool:
        return bool(self._client_id and self._access_token)
