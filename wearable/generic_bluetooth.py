"""Generic BLE adapter for pulse oximeters and BP cuffs.

Supports direct Bluetooth Low Energy data from common health devices.
Uses Bleak for cross-platform BLE support.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from wearable.base_adapter import BaseWearableAdapter, NormalizedBiosignals

logger = logging.getLogger(__name__)

_BLEAK_AVAILABLE = False
try:
    import bleak  # noqa: F401
    _BLEAK_AVAILABLE = True
except ImportError:
    pass


OXYMETER_SERVICE_UUIDS = [
    "00001822-0000-1000-8000-00805f9b34fb",
    "1822",
]
HR_SERVICE_UUIDS = [
    "0000180d-0000-1000-8000-00805f9b34fb",
    "180d",
]


class GenericBLEAdapter(BaseWearableAdapter):
    def __init__(self) -> None:
        self._device_address: str | None = None
        self._latest_hr: float | None = None
        self._latest_spo2: float | None = None

    async def authenticate(self) -> bool:
        return True

    async def connect(self, device_address: str) -> bool:
        if not _BLEAK_AVAILABLE:
            logger.warning("Bleak not installed — BLE unavailable")
            return False
        self._device_address = device_address
        return True

    async def fetch_recent_data(self) -> NormalizedBiosignals:
        result = NormalizedBiosignals(device_source="ble", timestamp=datetime.now(timezone.utc))
        if not _BLEAK_AVAILABLE or not self._device_address:
            return result

        try:
            from bleak import BleakScanner
            devices = await BleakScanner.discover(timeout=5.0)
            target = next((d for d in devices if d.address == self._device_address), None)
            if not target:
                result.data_freshness_minutes = 120
                return result

            from bleak import BleakClient
            async with BleakClient(target) as client:
                for svc_uuid in HR_SERVICE_UUIDS:
                    try:
                        hr_bytes = await client.read_gatt_char(f"{svc_uuid}-2a37")
                        if hr_bytes:
                            result.heart_rate_bpm = float(hr_bytes[1])
                            break
                    except Exception:
                        continue

                for svc_uuid in OXYMETER_SERVICE_UUIDS:
                    try:
                        spo2_bytes = await client.read_gatt_char(f"{svc_uuid}-2a5f")
                        if spo2_bytes:
                            result.spo2_percent = float(spo2_bytes[0])
                            break
                    except Exception:
                        continue

            result.data_freshness_minutes = 1
        except Exception:
            logger.exception("BLE data fetch failed")
        return result

    def is_available(self) -> bool:
        return _BLEAK_AVAILABLE and self._device_address is not None
