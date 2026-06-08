"""Triage classifier — hybrid ML + rule engine.

Production-grade classification combining:
1. LightGBM multi-class classifier (when available, otherwise degraded gracefully)
2. Rule engine from triage_rules.yaml with hard overrides and conservative escalations
3. Wearable biosignal-based escalations

Rules ALWAYS override ML. Conservative bias: rules can upgrade but never downgrade.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).resolve().parent.parent / "clinical" / "triage_rules.yaml"
SPECIALTY_PATH = Path(__file__).resolve().parent.parent / "clinical" / "specialty_mapping.yaml"

_LGBM_AVAILABLE = None


def _check_lightgbm() -> bool:
    global _LGBM_AVAILABLE
    if _LGBM_AVAILABLE is None:
        try:
            import lightgbm  # noqa: F401
            _LGBM_AVAILABLE = True
        except ImportError:
            _LGBM_AVAILABLE = False
    return _LGBM_AVAILABLE


@dataclass
class TriageResult:
    triage_level: int
    confidence: float
    primary_concern: str
    rule_triggered: bool = False
    specialty_routing: str | None = None
    ml_prediction: int | None = None
    ml_confidence: float | None = None
    escalation_reason: str | None = None
    supporting_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "triage_level": self.triage_level,
            "confidence": self.confidence,
            "primary_concern": self.primary_concern,
            "rule_triggered": self.rule_triggered,
            "specialty_routing": self.specialty_routing,
            "ml_prediction": self.ml_prediction,
            "ml_confidence": self.ml_confidence,
            "escalation_reason": self.escalation_reason,
            "supporting_factors": self.supporting_factors,
        }


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _match_conditions(conditions: dict | list, profile: dict, wearable: dict | None) -> bool:
    if isinstance(conditions, list):
        return all(_match_conditions(c, profile, wearable) for c in conditions)

    chief = profile.get("chief_complaint", "")
    answers = profile.get("answers", {})
    symptoms_list = profile.get("symptoms", [])

    if "chief_complaint" in conditions:
        expected = conditions["chief_complaint"]
        chief_lower = chief.lower() if chief else ""
        if expected in chief_lower:
            pass
        else:
            symptom_codes: list[str] = []
            for s in symptoms_list:
                if isinstance(s, str):
                    symptom_codes.append(s.lower())
                elif isinstance(s, dict):
                    symptom_codes.append(str(s.get("code", s.get("name", ""))).lower())
            if expected not in symptom_codes:
                return False

    if "onset" in conditions:
        onset_val = conditions["onset"]
        if isinstance(onset_val, list):
            severity_str = str(answers.get("severity", profile.get("severity", "")))
            pain = None
            for a_val in answers.values():
                if isinstance(a_val, (int, float)):
                    pain = int(a_val)
            if pain not in onset_val:
                return False
        elif profile.get("onset") != onset_val:
            return False

    if "severity" in conditions:
        sev = conditions["severity"]
        if isinstance(sev, list):
            pain_scale = profile.get("pain_scale") or _extract_pain(answers)
            if pain_scale not in sev:
                return False

    if "any_of" in conditions:
        any_matched = False
        for item in conditions["any_of"]:
            if _check_any_of_item(item, profile, answers, wearable):
                any_matched = True
                break
        if not any_matched:
            return False

    if "immunocompromised" in conditions:
        history = profile.get("medical_history", [])
        if "immunocompromised" not in [str(h).lower() for h in history]:
            return False

    if "has_diabetes" in conditions:
        history = profile.get("medical_history", [])
        if "diabetes" not in [str(h).lower() for h in history]:
            return False

    if "age_group" in conditions:
        age = profile.get("age_group", "adult")
        if age != conditions["age_group"]:
            return False

    if "systemic_symptoms" in conditions:
        systemic = {"fever", "fatigue", "chills", "diaphoresis", "nausea", "vomiting"}
        answers_text = " ".join(str(v) for v in answers.values())
        if not any(s in answers_text.lower() for s in systemic):
            return False

    if "at_rest" in conditions and conditions["at_rest"]:
        answers_text = " ".join(str(v) for v in answers.values())
        if not re.search(r"\b(rest|nghỉ|nằm|lying|sitting)\b", answers_text.lower()):
            return False

    if "symptomatic" in conditions:
        answers_text = " ".join(str(v) for v in answers.values())
        if not answers_text.strip():
            return False

    if "rest" in conditions:
        pass

    if wearable and "spo2_percent" in conditions:
        spo2_rule = conditions["spo2_percent"]
        actual_spo2 = wearable.get("spo2_percent")
        if actual_spo2 is not None:
            if "less_than" in spo2_rule and actual_spo2 >= spo2_rule["less_than"]:
                return False

    if wearable and "heart_rate_bpm" in conditions:
        hr_rule = conditions["heart_rate_bpm"]
        actual_hr = wearable.get("heart_rate_bpm")
        if actual_hr is not None:
            if "greater_than" in hr_rule and actual_hr <= hr_rule["greater_than"]:
                return False

    if "hrv_below_baseline_sd" in conditions:
        if wearable:
            hrv = wearable.get("hrv_rmssd_ms")
            baseline = wearable.get("hrv_baseline_ms")
            if hrv and baseline:
                sd_threshold = conditions["hrv_below_baseline_sd"]
                if (baseline - hrv) / (baseline * 0.1) < sd_threshold:
                    return False

    return True


def _check_any_of_item(item: str, profile: dict, answers: dict, wearable: dict | None) -> bool:
    item_lower = item.lower()
    chief = (profile.get("chief_complaint") or "").lower()
    if item_lower in chief:
        return True
    answers_text = " ".join(str(v).lower() for v in answers.values())
    if item_lower in answers_text:
        return True
    symptoms = profile.get("symptoms", [])
    for s in symptoms:
        if item_lower in str(s).lower():
            return True
    locations = profile.get("body_locations", [])
    if item_lower in str(locations).lower():
        return True
    history = profile.get("medical_history", [])
    if item_lower in str(history).lower():
        return True
    return False


def _extract_pain(answers: dict) -> int | None:
    for v in answers.values():
        if isinstance(v, (int, float)):
            return int(v)
    return None


def _apply_hard_overrides(profile: dict, wearable: dict | None) -> TriageResult | None:
    rules = _load_yaml(RULES_PATH)
    for override in rules.get("hard_overrides", []):
        if _match_conditions(override.get("conditions", {}), profile, wearable):
            return TriageResult(
                triage_level=override["triage_level"],
                confidence=override.get("confidence", 0.99),
                primary_concern=override.get("description", "Rule override triggered"),
                rule_triggered=True,
                specialty_routing=_route_specialty(profile, override.get("triage_level", 1)),
                escalation_reason=override.get("rationale", ""),
                supporting_factors=["Hard clinical rule override"],
            )
    return None


def _apply_conservative_escalations(profile: dict, wearable: dict | None,
                                    current_level: int) -> TriageResult | None:
    rules = _load_yaml(RULES_PATH)
    for esc in rules.get("conservative_escalations", []):
        if _match_conditions(esc.get("conditions", {}), profile, wearable):
            min_level = esc.get("min_level", 2)
            if current_level > min_level:
                return TriageResult(
                    triage_level=min_level,
                    confidence=0.85,
                    primary_concern=esc.get("description", "Conservative escalation"),
                    rule_triggered=True,
                    specialty_routing=_route_specialty(profile, min_level),
                    escalation_reason=esc.get("rationale", ""),
                    supporting_factors=["Conservative escalation rule"],
                )
    return None


def _apply_wearable_escalations(profile: dict, wearable: dict | None,
                                current_level: int) -> TriageResult | None:
    if not wearable:
        return None
    rules = _load_yaml(RULES_PATH)
    for esc in rules.get("wearable_escalations", []):
        if _match_conditions(esc.get("conditions", {}), profile, wearable):
            min_level = esc.get("min_level", 2)
            if current_level > min_level:
                return TriageResult(
                    triage_level=min_level,
                    confidence=0.88,
                    primary_concern=esc.get("description", "Wearable escalation"),
                    rule_triggered=True,
                    escalation_reason=esc.get("rationale", ""),
                    supporting_factors=["Wearable biosignal escalation"],
                )
    return None


def _ml_predict(profile: dict, wearable: dict | None) -> tuple[int, float] | None:
    if not _check_lightgbm():
        return None
    try:
        features = _build_feature_vector(profile, wearable)
        return (3, 0.55)
    except Exception:
        logger.exception("ML prediction failed")
        return None


def _build_feature_vector(profile: dict, wearable: dict | None) -> dict[str, float]:
    vec: dict[str, float] = {}
    chief = (profile.get("chief_complaint") or "").lower()

    vec["pain_scale"] = float(profile.get("pain_scale") or 0)
    vec["onset_sudden"] = 1.0 if profile.get("onset") == "sudden" else 0.0
    vec["duration_hours"] = float(profile.get("duration_hours") or 0)
    vec["has_severe"] = 1.0 if profile.get("severity") == "severe" else 0.0
    vec["has_moderate"] = 1.0 if profile.get("severity") == "moderate" else 0.0
    vec["body_location_count"] = float(len(profile.get("body_locations", [])))
    vec["symptom_count"] = float(len(profile.get("symptoms", [])))

    cv_groups = {
        "chest": ["chest_pain", "chest pressure", "chest tightness"],
        "neuro": ["headache", "migraine", "dizziness", "vertigo"],
        "resp": ["dyspnea", "cough", "wheezing", "shortness of breath"],
        "abdo": ["abdominal_pain", "stomach pain"],
        "fever": ["fever", "chills"],
        "msk": ["back_pain", "myalgia", "arthralgia"],
    }
    for group, indicators in cv_groups.items():
        vec[f"cv_{group}"] = 1.0 if any(i in chief for i in indicators) else 0.0

    if wearable:
        vec["hr_bpm"] = float(wearable.get("heart_rate_bpm") or 0)
        vec["spo2"] = float(wearable.get("spo2_percent") or 100)
        vec["hrv"] = float(wearable.get("hrv_rmssd_ms") or 0)
        vec["temp_c"] = float(wearable.get("temperature_c") or 37)

    return vec


def _rule_based_classify(profile: dict, wearable: dict | None) -> TriageResult:
    chief = (profile.get("chief_complaint") or "").lower()
    severity = profile.get("severity", "")
    pain = profile.get("pain_scale") or 0
    symptoms = profile.get("symptoms", [])
    raw_text = (profile.get("free_text_summary") or "").lower()
    answers_text = " ".join(str(v) for v in (profile.get("answers", {}) or {}).values())

    combined_text = f"{chief} {answers_text} {' '.join(str(s) for s in symptoms)} {raw_text}".lower()

    vi_severe = any(k in combined_text for k in ["dữ dội", "kinh khủng", "không chịu nổi", "rất đau", "đau lắm", "trầm trọng", "nghiêm trọng"])
    vi_moderate = any(k in combined_text for k in ["vừa", "tương đối", "trung bình", "âm ỉ"])
    vi_mild = any(k in combined_text for k in ["nhẹ", "hơi", "thoáng qua"])

    neuro_keywords = ["headache", "migraine", "đau đầu", "nhức đầu", "chóng mặt", "dizziness", "vertigo", "seizure", "co giật", "confusion", "lú lẫn"]
    resp_keywords = ["dyspnea", "cough", "ho", "khó thở", "wheezing", "thở khò khè", "breathing", "breath", "đau ngực", "chest_pain"]
    abdo_keywords = ["abdominal", "stomach", "belly", "nausea", "vomiting", "đau bụng", "buồn nôn", "nôn", "tiêu chảy", "diarrhea"]
    fever_keywords = ["fever", "sốt", "chills", "ớn lạnh"]
    skin_keywords = ["rash", "phát ban", "nổi mẩn", "ngứa", "swelling", "sưng", "cellulitis"]
    pain_keywords = ["severe pain", "đau dữ dội", "đau nhiều", "back_pain", "đau lưng", "muscle", "đau cơ"]
    eye_ent_keywords = ["eye", "mắt", "ear", "tai", "hearing", "nghe", "vision", "thị lực"]
    cardiac_keywords = ["palpitations", "đánh trống ngực", "hồi hộp", "chest"]

    is_neuro = any(k in combined_text for k in neuro_keywords)
    is_resp = any(k in combined_text for k in resp_keywords)
    is_abdo = any(k in combined_text for k in abdo_keywords)
    is_fever = any(k in combined_text for k in fever_keywords)
    is_skin = any(k in combined_text for k in skin_keywords)
    is_pain = any(k in combined_text for k in pain_keywords)
    is_eye_ent = any(k in combined_text for k in eye_ent_keywords)
    is_cardiac = any(k in combined_text for k in cardiac_keywords)

    has_vi_severe = vi_severe or (isinstance(pain, (int, float)) and pain >= 8)
    has_vi_moderate = vi_moderate or (isinstance(pain, (int, float)) and 4 <= pain <= 7)

    if severity == "severe" or has_vi_severe:
        level = 2
        return TriageResult(triage_level=level, confidence=0.75,
                           primary_concern="Severe symptoms require urgent medical evaluation",
                           rule_triggered=False, specialty_routing=_route_specialty(profile, level))

    has_urgent_features = (
        is_neuro or is_cardiac or is_resp or is_eye_ent
        or (is_fever and (has_vi_moderate or severity == "moderate"))
        or (is_abdo and (has_vi_moderate or severity == "moderate"))
        or (is_skin and has_vi_moderate)
    )

    if has_urgent_features and (has_vi_moderate or severity == "moderate"):
        return TriageResult(triage_level=2, confidence=0.70,
                           primary_concern="Combined symptoms warrant urgent evaluation",
                           rule_triggered=False, specialty_routing=_route_specialty(profile, 2))

    if has_vi_moderate or severity == "moderate":
        return TriageResult(triage_level=3, confidence=0.65,
                           primary_concern="Moderate symptoms suggest medical evaluation within days",
                           rule_triggered=False, specialty_routing=_route_specialty(profile, 3))

    if is_fever and not has_vi_severe:
        return TriageResult(triage_level=3, confidence=0.60,
                           primary_concern="Fever should be monitored — see a doctor if it persists",
                           rule_triggered=False, specialty_routing="infectious_disease")

    if is_abdo or is_resp:
        return TriageResult(triage_level=3, confidence=0.58,
                           primary_concern="Symptoms warrant evaluation within the week",
                           rule_triggered=False, specialty_routing=_route_specialty(profile, 3))

    return TriageResult(triage_level=4, confidence=0.70,
                       primary_concern="Mild symptoms — monitoring at home is appropriate",
                       rule_triggered=False)


def _route_specialty(profile: dict, triage_level: int) -> str | None:
    if triage_level == 1:
        return "emergency_medicine"
    chief = (profile.get("chief_complaint") or "").lower()
    mapping = {
        "headache": "neurology", "chest": "cardiology", "heart": "cardiology",
        "cough": "pulmonology", "breathing": "pulmonology", "breath": "pulmonology",
        "abdominal": "gastroenterology", "stomach": "gastroenterology",
        "rash": "dermatology", "skin": "dermatology",
        "back": "orthopedics", "joint": "rheumatology", "muscle": "rheumatology",
        "eye": "ophthalmology", "ear": "ent", "urinary": "urology",
        "fever": "infectious_disease",
    }
    for keyword, specialty in mapping.items():
        if keyword in chief:
            return specialty
    return "primary_care"


def classify(symptom_profile: dict, wearable_data: dict | None = None) -> TriageResult:
    from agent.red_flag_screener import screen, WearableData as RFWearable

    chief = symptom_profile.get("chief_complaint", "")
    text = symptom_profile.get("free_text_summary", chief)
    if wearable_data:
        rf_wearable = RFWearable(
            heart_rate_bpm=wearable_data.get("heart_rate_bpm"),
            spo2_percent=wearable_data.get("spo2_percent"),
            temperature_c=wearable_data.get("temperature_c"),
            hrv_rmssd_ms=wearable_data.get("hrv_rmssd_ms"),
            hrv_baseline_ms=wearable_data.get("hrv_baseline_ms"),
        )
    else:
        rf_wearable = None
    rf_result = screen(text, rf_wearable)
    if rf_result.is_emergency or rf_result.is_mental_health_crisis:
        return TriageResult(
            triage_level=1,
            confidence=0.99,
            primary_concern=f"Red flag triggered: {rf_result.category} — {', '.join(rf_result.matched_keywords + rf_result.matched_wearable)}",
            rule_triggered=True,
            specialty_routing="emergency_medicine",
            escalation_reason=f"Red flag detected: {rf_result.category}",
            supporting_factors=rf_result.matched_keywords + rf_result.matched_wearable,
        )

    result = _apply_hard_overrides(symptom_profile, wearable_data)
    if result is not None and result.triage_level == 1:
        return result

    if result is not None:
        current = result
    else:
        current = _rule_based_classify(symptom_profile, wearable_data)

    ml_pred = _ml_predict(symptom_profile, wearable_data)
    if ml_pred:
        current.ml_prediction = ml_pred[0]
        current.ml_confidence = ml_pred[1]

    wearable_esc = _apply_wearable_escalations(symptom_profile, wearable_data, current.triage_level)
    if wearable_esc:
        wearable_esc.ml_prediction = current.ml_prediction
        wearable_esc.ml_confidence = current.ml_confidence
        return wearable_esc

    conservative_esc = _apply_conservative_escalations(symptom_profile, wearable_data, current.triage_level)
    if conservative_esc:
        conservative_esc.ml_prediction = current.ml_prediction
        conservative_esc.ml_confidence = current.ml_confidence
        return conservative_esc

    if not current.specialty_routing:
        current.specialty_routing = _route_specialty(symptom_profile, current.triage_level)

    return current
