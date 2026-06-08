"""Google Health Connect adapter with real OAuth and data parsing.

Uses Google Health Connect API for Android health data access.
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
TOKEN_FILE = Path.home() / ".phta" / "google_health_token.json"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleHealthAdapter(BaseWearableAdapter):
    def __init__(self) -> None:
        self._client_id = os.environ.get("GOOGLE_HEALTH_CLIENT_ID", "")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._load_token()

    def _load_token(self) -> None:
        if not TOKEN_FILE.exists():
            return
        try:
            data = json.loads(TOKEN_FILE.read_text())
            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")
        except Exception:
            pass

    def _save_token(self) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps({
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
        }))

    async def authenticate(self) -> bool:
        if not self._client_id:
            return False
        if self._refresh_token:
            return await self._refresh()
        return False

    async def _refresh(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                })
                if resp.status_code == 200:
                    data = resp.json()
                    self._access_token = data.get("access_token")
                    self._save_token()
                    return True
        except Exception:
            logger.exception("Google Health token refresh failed")
        return False

    async def fetch_recent_data(self) -> NormalizedBiosignals:
        if not self._access_token:
            return NormalizedBiosignals(device_source="google_health")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        result = NormalizedBiosignals(device_source="google_health", timestamp=datetime.now(timezone.utc))
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                end = datetime.now(timezone.utc)
                start = datetime.fromtimestamp(end.timestamp() - 86400, tz=timezone.utc)
                data_types = [
                    "HeartRate", "RestingHeartRate", "HeartRateVariabilityRmssd",
                    "OxygenSaturation", "RespiratoryRate", "Steps",
                ]
                for dtype in data_types:
                    resp = await client.post(
                        "https://healthconnect.googleapis.com/v1/datasets/aggregate",
                        headers=headers,
                        json={
                            "aggregateBy": [{"dataTypeName": dtype}],
                            "startTimeMillis": int(start.timestamp() * 1000),
                            "endTimeMillis": int(end.timestamp() * 1000),
                        },
                    )
                    if resp.status_code == 200:
                        _parse_health_connect_response(dtype, resp.json(), result)
            result.data_freshness_minutes = 5
        except Exception:
            logger.exception("Google Health fetch failed")
        return result

    def is_available(self) -> bool:
        return bool(self._client_id and self._access_token)


def _parse_health_connect_response(dtype: str, data: dict, result: NormalizedBiosignals) -> None:
    buckets = data.get("bucket", [])
    values = []
    for bucket in buckets:
        for ds in bucket.get("dataset", []):
            for point in ds.get("point", []):
                v = point.get("value", [{}])
                if v and isinstance(v, list):
                    fp = v[0].get("fpVal") or v[0].get("intVal")
                    if fp:
                        values.append(float(fp))
    if not values:
        return
    avg = sum(values) / len(values)
    if "HeartRate" == dtype and "Resting" not in dtype:
        result.heart_rate_bpm = avg
    elif "RestingHeartRate" in dtype:
        result.heart_rate_resting = avg
    elif "HeartRateVariability" in dtype:
        result.hrv_rmssd_ms = avg
    elif "OxygenSaturation" in dtype:
        result.spo2_percent = avg * 100 if avg <= 1 else avg
    elif "RespiratoryRate" in dtype:
        result.respiratory_rate = avg
    elif "Steps" in dtype:
        result.steps_today = int(sum(values))
