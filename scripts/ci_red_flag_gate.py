"""CI Red Flag Gate — blocks merge if any EMERGENCY fixture fails.

Reads clinical/fixtures/red_flag_cases.yaml and verifies that every
case triggers EMERGENCY from red_flag_screener.py.

Exit codes:
  0 — ALL cases passed (EMERGENCY correctly triggered)
  1 — One or more cases failed (safety regression)
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Windows console Unicode fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.red_flag_screener import WearableData, screen

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "clinical" / "fixtures" / "red_flag_cases.yaml"


def main() -> int:
    if not FIXTURES_PATH.exists():
        print(f"Fixture file not found: {FIXTURES_PATH}")
        return 1

    with open(FIXTURES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("cases", [])
    if not cases:
        print("No cases found in red_flag_cases.yaml")
        return 1

    failed = []
    for case in cases:
        wearable = None
        if case.get("wearable_data"):
            wd = case["wearable_data"]
            wearable = WearableData(
                heart_rate_bpm=wd.get("heart_rate_bpm"),
                spo2_percent=wd.get("spo2_percent"),
                temperature_c=wd.get("temperature_c"),
            )

        result = screen(case["input_text"], wearable)

        if not result.is_emergency and not result.is_mental_health_crisis:
            failed.append(
                f"  FAILED: {case['id']} - {case['description']}\n"
                f"    Input: {case['input_text']}\n"
                f"    Expected: EMERGENCY, Got: category={result.category}, emergency={result.is_emergency}"
            )

    if failed:
        print(f"RED FLAG GATE FAILED — {len(failed)}/{len(cases)} cases did NOT trigger EMERGENCY:\n")
        for f_msg in failed:
            print(f_msg)
        print("\n⛔ This is a patient safety regression. Fix before merging.")
        return 1

    print(f"✓ RED FLAG GATE PASSED — All {len(cases)} EMERGENCY fixtures correctly triggered EMERGENCY.")
    print("✓ Safe to merge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
