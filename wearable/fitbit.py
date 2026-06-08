"""Fitbit Web API adapter with real OAuth 2.0 flow and data parsing.

Requires: FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET env vars.
Uses Fitbit Web API v1 for intraday heart rate, SpO2, sleep, and activity data.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from wearable.base_adapter import BaseWearableAdapter, NormalizedBiosignals

logger = logging.getLogger(__name__)

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_API_BASE = "https://api.fitbit.com/1/user/-"
TOKEN_FILE = Path.home() / ".phta" / "fitbit_token.json"


class FitbitAdapter(BaseWearableAdapter):
    def __init__(self) -> None:
        self._client_id = os.environ.get("FITBIT_CLIENT_ID", "")
        self._client_secret = os.environ.get("FITBIT_CLIENT_SECRET", "")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: datetime | None = None
        self._load_token()

    def _load_token(self) -> None:
        if not TOKEN_FILE.exists():
            return
        try:
            data = json.loads(TOKEN_FILE.read_text())
            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")
            expiry_str = data.get("expires_at")
            if expiry_str:
                self._token_expiry = datetime.fromisoformat(expiry_str)
        except Exception:
            logger.exception("Failed to load Fitbit token")

    def _save_token(self) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "expires_at": self._token_expiry.isoformat() if self._token_expiry else None,
        }
        TOKEN_FILE.write_text(json.dumps(data))

    async def authenticate(self) -> bool:
        if not self._client_id or not self._client_secret:
            logger.warning("Fitbit credentials not configured")
            return False
        if self._access_token and self._token_expiry and self._token_expiry > datetime.now(timezone.utc):
            return True
        if not self._refresh_token:
            auth_url = f"{FITBIT_AUTH_URL}?client_id={self._client_id}&response_type=code&scope=activity+heartrate+location+nutrition+profile+settings+sleep+social+weight&redirect_uri=http://localhost:8000/wearable/fitbit/callback"
            logger.info(f"Fitbit OAuth URL: {auth_url}")
            return False
        return await self._refresh()

    async def _refresh(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(FITBIT_TOKEN_URL, data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                })
                if resp.status_code == 200:
                    data = resp.json()
                    self._access_token = data["access_token"]
                    self._refresh_token = data.get("refresh_token", self._refresh_token)
                    self._token_expiry = datetime.fromtimestamp(
                        datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600)
                    )
                    self._save_token()
                    return True
        except Exception:
            logger.exception("Fitbit token refresh failed")
        return False

    async def fetch_recent_data(self) -> NormalizedBiosignals:
        if not self._access_token:
            return NormalizedBiosignals(device_source="fitbit")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        result = NormalizedBiosignals(device_source="fitbit", timestamp=datetime.now(timezone.utc))
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                hr_resp = await client.get(f"{FITBIT_API_BASE}/activities/heart/date/today/1d/1min.json", headers=headers)
                if hr_resp.status_code == 200:
                    hr_data = hr_resp.json()
                    intra = hr_data.get("activities-heart-intraday", {}).get("dataset", [])
                    if intra:
                        hr_values = [d["value"] for d in intra if d.get("value")]
                        if hr_values:
                            result.heart_rate_bpm = sum(hr_values[-10:]) / min(10, len(hr_values[-10:]))
                    resting = hr_data.get("activities-heart", [{}])[0].get("value", {}).get("restingHeartRate", 0) if hr_data.get("activities-heart") else None
                    if resting and resting > 0:
                        result.heart_rate_resting = float(resting)

                spo2_resp = await client.get(f"{FITBIT_API_BASE}/spo2/date/today.json", headers=headers)
                if spo2_resp.status_code == 200:
                    spo2_data = spo2_resp.json()
                    spo2_minutes = spo2_data.get("minutes", [])
                    if spo2_minutes:
                        spo2_values = [m["value"] for m in spo2_minutes if m.get("value")]
                        if spo2_values:
                            result.spo2_percent = sum(spo2_values) / len(spo2_values)

                sleep_resp = await client.get(f"{FITBIT_API_BASE}/sleep/date/today.json", headers=headers)
                if sleep_resp.status_code == 200:
                    sleep_data = sleep_resp.json()
                    sleep_records = sleep_data.get("sleep", [])
                    if sleep_records:
                        result.sleep_hours_last_night = float(sleep_records[0].get("minutesAsleep", 0)) / 60.0

            result.data_freshness_minutes = 5
        except Exception:
            logger.exception("Fitbit data fetch failed")
        return result

    def is_available(self) -> bool:
        return bool(self._client_id and self._client_secret and self._access_token)


async def oauth_callback(code: str) -> bool:
    adapter = FitbitAdapter()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(FITBIT_TOKEN_URL, data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": adapter._client_id,
                "client_secret": adapter._client_secret,
                "redirect_uri": "http://localhost:8000/wearable/fitbit/callback",
            })
            if resp.status_code == 200:
                data = resp.json()
                adapter._access_token = data["access_token"]
                adapter._refresh_token = data.get("refresh_token")
                adapter._token_expiry = datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600)
                )
                adapter._save_token()
                return True
    except Exception:
        logger.exception("Fitbit OAuth callback failed")
    return False
