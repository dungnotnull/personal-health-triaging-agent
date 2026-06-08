"""Clinical validation runner — runs all fixture cases against PHTA.

Calculates accuracy, false negative rate, false positive rate, and
per-category breakdown. Generates a validation report.

Usage:
    python tests/harness.py              # Run all fixtures
    python tests/harness.py --red-flags  # Red flag fixtures only
    python tests/harness.py --symptoms   # Symptom cases only
    python tests/harness.py --report     # Generate validation report
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.red_flag_screener import WearableData, screen as red_flag_screen
from agent.triage_classifier import classify as triage_classify
from nlp.symptom_extractor import extract_symptoms

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "clinical" / "fixtures"

TRIAGE_NAMES = {1: "EMERGENCY", 2: "URGENT", 3: "SEMI-URGENT", 4: "NON-URGENT"}


def _load_fixtures(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("cases", [])


def _parse_wearable(case: dict) -> WearableData | None:
    wd = case.get("wearable_data")
    if not wd:
        return None
    return WearableData(
        heart_rate_bpm=wd.get("heart_rate_bpm"),
        spo2_percent=wd.get("spo2_percent"),
        temperature_c=wd.get("temperature_c"),
    )


def validate_red_flags() -> dict:
    cases = _load_fixtures(FIXTURES_DIR / "red_flag_cases.yaml")
    passed = 0
    failed = []
    for case in cases:
        wearable = _parse_wearable(case)
        result = red_flag_screen(case["input_text"], wearable)
        if result.is_emergency or result.is_mental_health_crisis:
            passed += 1
        else:
            failed.append({
                "id": case["id"],
                "description": case.get("description", ""),
                "input": case["input_text"][:80],
                "expected": TRIAGE_NAMES.get(case["expected_triage"], "EMERGENCY"),
                "got_category": result.category,
                "got_emergency": result.is_emergency,
            })

    total = len(cases)
    return {
        "test_type": "red_flag_emergency",
        "total": total,
        "passed": passed,
        "failed": len(failed),
        "pass_rate": (passed / total * 100) if total > 0 else 0,
        "failures": failed,
        "gate_passed": len(failed) == 0,
    }


def validate_symptom_cases() -> dict:
    cases = _load_fixtures(FIXTURES_DIR / "symptom_cases.yaml")
    results = {
        "test_type": "symptom_cases",
        "total": len(cases),
        "correct": 0,
        "incorrect": 0,
        "false_negatives": 0,
        "false_positives": 0,
        "by_level": {1: {"total": 0, "correct": 0}, 2: {"total": 0, "correct": 0},
                     3: {"total": 0, "correct": 0}, 4: {"total": 0, "correct": 0}},
        "errors": [],
    }

    for case in cases:
        expected = case["expected_triage"]
        results["by_level"][expected]["total"] += 1

        actual = _classify_case(case)
        if actual == expected:
            results["correct"] += 1
            results["by_level"][expected]["correct"] += 1
        else:
            results["incorrect"] += 1
            if actual > expected:
                results["false_negatives"] += 1
            else:
                results["false_positives"] += 1
            results["errors"].append({
                "id": case["id"],
                "description": case.get("description", "")[:100],
                "expected": expected,
                "actual": actual,
                "expected_name": TRIAGE_NAMES.get(expected, ""),
                "actual_name": TRIAGE_NAMES.get(actual, ""),
            })

    total = results["total"]
    results["accuracy"] = (results["correct"] / total * 100) if total > 0 else 0
    return results


def _classify_case(case: dict) -> int:
    text = case["input_text"]
    wearable = _parse_wearable(case)

    profile = extract_symptoms(text)
    wearable_dict = case.get("wearable_data", {}) if case.get("wearable_data") else None
    if wearable and wearable_dict is None:
        wearable_dict = {
            "heart_rate_bpm": wearable.heart_rate_bpm,
            "spo2_percent": wearable.spo2_percent,
            "temperature_c": wearable.temperature_c,
        }
    result = triage_classify(profile, wearable_dict)
    return result.triage_level


def validate_false_negatives() -> dict:
    cases = _load_fixtures(FIXTURES_DIR / "false_negative_cases.yaml")
    passed = 0
    failed = []
    for case in cases:
        actual = _classify_case(case)
        if actual == 1:
            passed += 1
        else:
            failed.append({
                "id": case["id"],
                "description": case.get("description", ""),
                "input": case["input_text"][:80],
                "expected": "EMERGENCY",
                "got_level": actual,
                "notes": case.get("notes", ""),
            })

    total = len(cases)
    return {
        "test_type": "false_negative_emergency",
        "total": total,
        "passed": passed,
        "failed": len(failed),
        "pass_rate": (passed / total * 100) if total > 0 else 0,
        "failures": failed,
        "fnr": (len(failed) / total * 100) if total > 0 else 0,
    }


def run_all() -> dict:
    rf = validate_red_flags()
    fn = validate_false_negatives()
    sc = validate_symptom_cases()

    return {
        "red_flag_gate": {"passed": rf["gate_passed"], "pass_rate": rf["pass_rate"], "total": rf["total"]},
        "false_negative_gate": {"passed": fn["failed"] == 0, "pass_rate": fn["pass_rate"], "total": fn["total"]},
        "symptom_accuracy": {"accuracy": sc["accuracy"], "total": sc["total"], "correct": sc["correct"]},
        "by_triage_level": {
            str(level): {
                "accuracy": (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0,
                "total": data["total"],
                "correct": data["correct"],
            }
            for level, data in sc["by_level"].items()
        },
        "gate_result": "PASSED" if rf["gate_passed"] and fn["failed"] == 0 else "FAILED",
        "errors": sc.get("errors", [])[:20],
    }


def generate_report() -> str:
    results = run_all()
    lines = [
        "=" * 60,
        "  PHTA CLINICAL VALIDATION REPORT",
        "=" * 60,
        "",
        f"  Gate Result: {results['gate_result']}",
        "",
        "--- Red Flag Emergency Gate ---",
        f"  Pass Rate: {results['red_flag_gate']['pass_rate']:.1f}% ({results['red_flag_gate']['total']} cases)",
        "",
        "--- False Negative Emergency Gate ---",
        f"  Pass Rate: {results['false_negative_gate']['pass_rate']:.1f}% ({results['false_negative_gate']['total']} cases)",
        "",
        "--- Symptom Triage Accuracy ---",
        f"  Overall: {results['symptom_accuracy']['accuracy']:.1f}% ({results['symptom_accuracy']['correct']}/{results['symptom_accuracy']['total']})",
        "",
    ]
    for level, data in sorted(results["by_triage_level"].items()):
        lines.append(f"  Level {level} ({TRIAGE_NAMES.get(int(level), 'UNKNOWN')}): {data['accuracy']:.1f}% ({data['correct']}/{data['total']})")

    if results["errors"]:
        lines.append("")
        lines.append("--- Classification Errors (first 20) ---")
        for err in results["errors"][:20]:
            lines.append(f"  [{err['id']}] Expected {err['expected_name']}, Got {err['actual_name']}: {err['description']}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="PHTA Clinical Validation Runner")
    parser.add_argument("--red-flags", action="store_true", help="Run red flag gate only")
    parser.add_argument("--symptoms", action="store_true", help="Run symptom accuracy only")
    parser.add_argument("--false-negatives", action="store_true", help="Run false negative gate only")
    parser.add_argument("--report", action="store_true", help="Generate full validation report")
    args = parser.parse_args()

    if args.red_flags:
        result = validate_red_flags()
        print(f"Red Flag Gate: {result['pass_rate']:.1f}% ({result['passed']}/{result['total']})")
        if result["failures"]:
            for f in result["failures"]:
                print(f"  FAIL: [{f['id']}] {f['description']}")
    elif args.symptoms:
        result = validate_symptom_cases()
        print(f"Symptom Accuracy: {result['accuracy']:.1f}% ({result['correct']}/{result['total']})")
    elif args.false_negatives:
        result = validate_false_negatives()
        print(f"False Negative Gate: {result['pass_rate']:.1f}% ({result['passed']}/{result['total']})")
    elif args.report:
        print(generate_report())
    else:
        print(generate_report())


if __name__ == "__main__":
    main()
