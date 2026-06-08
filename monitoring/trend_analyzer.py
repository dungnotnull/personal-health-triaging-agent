"""Trend analyzer — detect improving/deteriorating/stable health patterns.

Analyzes health timeline data for trend direction using pain score
trajectories, symptom frequency changes, and wearable biosignal deltas.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class Trend(Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"


class TrendAnalyzer:
    def __init__(self) -> None:
        pass

    def analyze(self, timeline: list[dict[str, Any]]) -> Trend:
        if not timeline:
            return Trend.STABLE
        if len(timeline) < 2:
            return Trend.STABLE

        scores = []
        for entry in sorted(timeline, key=lambda e: e.get("timestamp", "")):
            data = entry.get("data", {})
            pain = data.get("pain_scale")
            if pain is not None:
                scores.append(float(pain))
            if "severity" in data:
                sev_map = {"mild": 2, "moderate": 5, "severe": 8, "unspecified": 4}
                scores.append(sev_map.get(data["severity"], 4))

        if len(scores) < 2:
            return Trend.STABLE

        n = min(5, len(scores))
        recent = scores[-n:]
        older = scores[-n*2:-n] if len(scores) >= n*2 else scores[:-1]
        if not older:
            return Trend.STABLE

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        delta = recent_avg - older_avg
        if delta < -1.5:
            return Trend.IMPROVING
        elif delta > 1.5:
            return Trend.WORSENING
        return Trend.STABLE

    def analyze_wearable_trend(self, readings: list[dict[str, Any]]) -> dict[str, Trend]:
        trends: dict[str, Trend] = {}
        metrics = ["heart_rate_bpm", "spo2_percent", "hrv_rmssd_ms", "temperature_c"]
        for metric in metrics:
            values = [r.get(metric) for r in readings if r.get(metric) is not None]
            if len(values) < 3:
                trends[metric] = Trend.STABLE
                continue
            recent = sum(values[-3:]) / 3
            older = sum(values[-6:-3]) / max(len(values[-6:-3]), 1) if len(values) >= 6 else values[0]
            delta = recent - older
            if metric == "spo2_percent":
                if delta < -2:
                    trends[metric] = Trend.WORSENING
                elif delta > 2:
                    trends[metric] = Trend.IMPROVING
                else:
                    trends[metric] = Trend.STABLE
            elif metric == "hrv_rmssd_ms":
                if delta < -10:
                    trends[metric] = Trend.WORSENING
                elif delta > 10:
                    trends[metric] = Trend.IMPROVING
                else:
                    trends[metric] = Trend.STABLE
            else:
                if delta > 8:
                    trends[metric] = Trend.WORSENING
                elif delta < -8:
                    trends[metric] = Trend.IMPROVING
                else:
                    trends[metric] = Trend.STABLE
        return trends

    def should_escalate(self, timeline: list[dict[str, Any]],
                        wearable_data: dict[str, Any] | None = None) -> bool:
        trend = self.analyze(timeline)
        if trend == Trend.WORSENING:
            return True
        if wearable_data:
            spo2 = wearable_data.get("spo2_percent")
            if spo2 is not None and spo2 < 94:
                return True
            hr = wearable_data.get("heart_rate_bpm")
            if hr is not None and (hr > 120 or hr < 50):
                return True
        return False
