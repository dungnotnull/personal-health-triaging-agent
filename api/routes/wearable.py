"""Wearable OAuth callbacks, data sync endpoints."""

from fastapi import APIRouter, HTTPException
from agent.red_flag_screener import WearableData, screen

router = APIRouter(prefix="/wearable", tags=["wearable"])


@router.get("/fitbit/callback")
async def fitbit_callback(code: str = ""):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")
    from wearable.fitbit import oauth_callback
    success = await oauth_callback(code)
    return {"status": "connected" if success else "failed", "device": "fitbit"}


@router.post("/data")
async def receive_wearable_data(request: dict):
    wearable = WearableData(
        heart_rate_bpm=request.get("heart_rate_bpm"),
        spo2_percent=request.get("spo2_percent"),
        temperature_c=request.get("temperature_c"),
    )
    result = screen("", wearable)
    return {
        "alerts": result.matched_wearable,
        "is_emergency": result.is_emergency,
        "category": result.category,
    }


@router.get("/status")
async def wearable_status():
    return {
        "devices": {
            "fitbit": _check_device("fitbit"),
            "google_health": _check_device("google_health"),
            "garmin": _check_device("garmin"),
            "apple_health": _check_device("apple_health"),
            "ble": _check_device("ble"),
        }
    }


def _check_device(name: str) -> dict:
    try:
        if name == "fitbit":
            from wearable.fitbit import FitbitAdapter
            a = FitbitAdapter()
            return {"available": a.is_available(), "authenticated": a._access_token is not None}
        elif name == "google_health":
            from wearable.google_health import GoogleHealthAdapter
            a = GoogleHealthAdapter()
            return {"available": a.is_available(), "authenticated": a._access_token is not None}
        elif name == "garmin":
            from wearable.garmin import GarminAdapter
            a = GarminAdapter()
            return {"available": a.is_available(), "authenticated": a._access_token is not None}
        elif name == "apple_health":
            from wearable.apple_health import AppleHealthAdapter
            a = AppleHealthAdapter()
            return {"available": a.is_available(), "authenticated": True}
        elif name == "ble":
            from wearable.generic_bluetooth import GenericBLEAdapter
            a = GenericBLEAdapter()
            return {"available": a.is_available(), "authenticated": True}
    except Exception:
        pass
    return {"available": False, "authenticated": False}
