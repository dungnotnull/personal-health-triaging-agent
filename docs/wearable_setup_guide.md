# Wearable Device Setup Guide

## Supported Devices

| Platform | Data Available | Setup Method |
|----------|---------------|--------------|
| Apple HealthKit | HR, HRV, SpO2, steps, sleep, temperature, ECG | iOS Shortcuts export → HTTP webhook |
| Google Health Connect | HR, SpO2, steps, sleep, blood pressure | Android Health Connect API |
| Fitbit | HR, HRV, SpO2, sleep stages, skin temp | Fitbit Web API (OAuth 2.0) |
| Garmin Connect | HR, HRV, SpO2, stress score, sleep | Garmin Health API |
| Generic BLE | SpO2, HR (pulse oximeters) | Web Bluetooth API or BLE serial |

## Manual Vital Sign Entry

You can also enter vital signs manually via text or voice:
- "SpO2 là 96%"
- "Heart rate 72 bpm"
- "Nhiệt độ 37.5 độ C"
- "My temperature is 98.6 F"

PHTA will parse these values and include them in the triage evaluation.

## Setup Instructions

### Fitbit

1. Register a Fitbit Web API application at https://dev.fitbit.com
2. Set redirect URI to `http://localhost:8000/wearable/fitbit/callback`
3. Add your credentials to `.env`:
   ```
   FITBIT_CLIENT_ID=your_client_id
   FITBIT_CLIENT_SECRET=your_client_secret
   ```
4. Run `phta wearable setup fitbit` and follow the OAuth flow

### Google Health Connect

1. Enable Google Health Connect API in Google Cloud Console
2. Set `GOOGLE_HEALTH_CLIENT_ID` in `.env`
3. Grant permissions in the Android Health Connect app

### Apple HealthKit

Requires the PHTA iOS companion app (Phase 3). For now, you can export HealthKit data via iOS Shortcuts and import manually.

### Garmin Connect

1. Register at https://developer.garmin.com
2. Set `GARMIN_CLIENT_ID` in `.env`
3. Run `phta wearable setup garmin`

## Data Freshness

PHTA displays how recent your wearable data is:
- **< 5 minutes ago:** Current reading
- **< 1 hour ago:** Recent reading
- **> 1 hour ago:** Stale reading (may not reflect current state)
- **> 24 hours ago:** Not used for triage evaluation

## Troubleshooting

- **No data appearing:** Ensure the device synced within the last hour
- **SpO2 readings seem low:** Consumer pulse oximeters can be inaccurate by ±2-3%
- **HRV data missing:** Not all devices support HRV; check your device specs
- **Sleep data incomplete:** Ensure you wore the device to sleep and it synced in the morning
