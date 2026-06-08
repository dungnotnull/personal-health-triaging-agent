"""Apple HealthKit adapter — HTTP webhook receiver.

Receives HealthKit exports via iOS Shortcuts HTTP webhook.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from wearable.base_adapter import BaseWearableAdapter, NormalizedBiosignals

logger = logging.getLogger(__name__)


class AppleHealthAdapter(BaseWearableAdapter):
    def __init__(self) -> None:
        self._latest_data: dict = {}

    async def authenticate(self) -> bool:
        return True

    async def fetch_recent_data(self) -> NormalizedBiosignals:
        from wearable.normalizer import normalize_apple_health
        if not self._latest_data:
            return NormalizedBiosignals(device_source="apple_health")
        result = normalize_apple_health(self._latest_data)
        result.data_freshness_minutes = self._freshness(
            self._latest_data.get("endDate")
        )
        return result

    def receive_webhook(self, data: dict) -> None:
        self._latest_data = data
        logger.info("Apple Health data received via webhook")

    def is_available(self) -> bool:
        return bool(self._latest_data)

    @staticmethod
    def _freshness(ts_str: str | None) -> int:
        if not ts_str:
            return 60
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return max(1, int((datetime.now(timezone.utc) - ts).total_seconds() / 60))
        except Exception:
            return 60
