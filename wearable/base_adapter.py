"""Abstract wearable device adapter.

Defines the interface that all wearable integrations must implement.
Each concrete adapter handles authentication, data fetching, and
normalization for a specific device platform.

Supported platforms (Phase 2+):
  - Apple HealthKit
  - Google Health Connect
  - Fitbit Web API
  - Garmin Connect API
  - Generic BLE (pulse oximeter, BP cuff)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class NormalizedBiosignals:
    heart_rate_bpm: float | None = None
    heart_rate_resting: float | None = None
    hrv_rmssd_ms: float | None = None
    spo2_percent: float | None = None
    respiratory_rate: float | None = None
    skin_temperature_c: float | None = None
    sleep_hours_last_night: float | None = None
    sleep_quality_score: float | None = None
    stress_score: float | None = None
    steps_today: int | None = None
    timestamp: datetime | None = None
    device_source: str = "unknown"
    data_freshness_minutes: int = 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "heart_rate_bpm": self.heart_rate_bpm,
            "heart_rate_resting": self.heart_rate_resting,
            "hrv_rmssd_ms": self.hrv_rmssd_ms,
            "spo2_percent": self.spo2_percent,
            "respiratory_rate": self.respiratory_rate,
            "skin_temperature_c": self.skin_temperature_c,
            "sleep_hours_last_night": self.sleep_hours_last_night,
            "sleep_quality_score": self.sleep_quality_score,
            "stress_score": self.stress_score,
            "steps_today": self.steps_today,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "device_source": self.device_source,
            "data_freshness_minutes": self.data_freshness_minutes,
        }


class BaseWearableAdapter(ABC):
    """Abstract base for all wearable device adapters."""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the device platform. Returns True on success."""
        ...

    @abstractmethod
    async def fetch_recent_data(self) -> NormalizedBiosignals:
        """Fetch and normalize the most recent biosignal data."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the device/platform is configured and reachable."""
        ...
