"""Wearable device data normalizer — production cross-platform standardisation.

Converts raw readings from Apple Health, Google Health Connect, Fitbit,
Garmin, BLE devices into a unified NormalizedBiosignals structure.
Handles unit conversion, timestamp normalisation, and quality scoring.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from wearable.base_adapter import NormalizedBiosignals


def _parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def normalize_apple_health(raw: dict) -> NormalizedBiosignals:
    records = raw.get("data", {}).get("metrics", [])
    result = NormalizedBiosignals(device_source="apple_health")
    for metric in records:
        name = metric.get("name", "")
        val = metric.get("value")
        if name == "heart_rate" and val:
            result.heart_rate_bpm = float(val)
        elif name == "resting_heart_rate" and val:
            result.heart_rate_resting = float(val)
        elif name == "heart_rate_variability" and val:
            result.hrv_rmssd_ms = float(val)
        elif name == "oxygen_saturation" and val:
            result.spo2_percent = float(val) * 100 if float(val) <= 1 else float(val)
        elif name == "respiratory_rate" and val:
            result.respiratory_rate = float(val)
        elif name == "body_temperature" and val:
            result.skin_temperature_c = float(val)
        elif name == "sleep_hours" and val:
            result.sleep_hours_last_night = float(val)
        elif name == "step_count" and val:
            result.steps_today = int(float(val))
    result.timestamp = _parse_ts(raw.get("endDate"))
    result.data_freshness_minutes = _freshness(result.timestamp)
    return result


def normalize_google_health(raw: dict) -> NormalizedBiosignals:
    result = NormalizedBiosignals(device_source="google_health")
    dp = raw.get("dataPoints", []) if isinstance(raw, dict) else raw
    if isinstance(dp, list):
        for point in dp:
            fname = point.get("dataTypeName", "")
            values = point.get("values", [])
            val = float(values[0].get("value", 0)) if values else None
            if "heart_rate" in fname and "resting" not in fname:
                result.heart_rate_bpm = val
            elif "resting_heart_rate" in fname:
                result.heart_rate_resting = val
            elif "heart_rate_variability" in fname:
                result.hrv_rmssd_ms = val
            elif "oxygen_saturation" in fname:
                result.spo2_percent = val
            elif "respiratory_rate" in fname:
                result.respiratory_rate = val
            elif "body_temperature" in fname:
                result.skin_temperature_c = val
            elif "sleep" in fname:
                result.sleep_hours_last_night = float(val or 0) / 60.0 if val else None
            elif "steps" in fname:
                result.steps_today = int(float(val or 0))
    result.timestamp = datetime.now(timezone.utc)
    result.data_freshness_minutes = 5
    return result


def normalize_fitbit(raw: dict) -> NormalizedBiosignals:
    result = NormalizedBiosignals(device_source="fitbit")
    hr_data = raw.get("activities-heart", [])
    if isinstance(hr_data, list) and hr_data:
        latest = hr_data[-1]
        resting = latest.get("value", {}).get("restingHeartRate")
        if resting:
            result.heart_rate_resting = float(resting)
    hr_intra = raw.get("activities-heart-intraday", {})
    intra_dataset = hr_intra.get("dataset", [])
    if intra_dataset:
        result.heart_rate_bpm = float(intra_dataset[-1].get("value", 0))
    spo2 = raw.get("spo2", {})
    spo2_val = spo2.get("avg") if isinstance(spo2, dict) else None
    if spo2_val:
        result.spo2_percent = float(spo2_val)
    sleep_data = raw.get("sleep", [])
    if isinstance(sleep_data, list) and sleep_data:
        latest_sleep = sleep_data[0]
        minutes = latest_sleep.get("minutesAsleep") or latest_sleep.get("duration", 0)
        result.sleep_hours_last_night = float(minutes) / 60.0
    result.timestamp = _parse_ts(raw.get("timestamp"))
    result.data_freshness_minutes = _freshness(result.timestamp)
    return result


def normalize_garmin(raw: dict) -> NormalizedBiosignals:
    result = NormalizedBiosignals(device_source="garmin")
    result.heart_rate_bpm = _float_or_none(raw.get("heartRate"))
    result.heart_rate_resting = _float_or_none(raw.get("restingHeartRate"))
    result.stress_score = _float_or_none(raw.get("stressScore"))
    result.steps_today = _int_or_none(raw.get("steps"))
    spo2 = raw.get("spo2")
    if spo2:
        result.spo2_percent = _float_or_none(spo2)
    result.timestamp = _parse_ts(raw.get("timestamp"))
    result.data_freshness_minutes = _freshness(result.timestamp)
    return result


def normalize_ble(raw: dict) -> NormalizedBiosignals:
    result = NormalizedBiosignals(device_source="ble")
    result.spo2_percent = _float_or_none(raw.get("spo2") or raw.get("SpO2"))
    result.heart_rate_bpm = _float_or_none(raw.get("hr") or raw.get("heartRate") or raw.get("pulse"))
    result.skin_temperature_c = _float_or_none(raw.get("temp") or raw.get("temperature"))
    result.timestamp = datetime.now(timezone.utc)
    result.data_freshness_minutes = 1
    return result


def _float_or_none(val: Any) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _int_or_none(val: Any) -> int | None:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _freshness(ts: datetime | None) -> int:
    if ts is None:
        return 60
    delta = (datetime.now(timezone.utc) - ts).total_seconds()
    return max(1, int(delta / 60))
