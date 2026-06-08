"""Structured symptom profile extraction from free text.

Integrates medical NER and severity parser to produce a complete
symptom profile dict from natural language input. Works fully offline
without any model dependencies.
"""

from __future__ import annotations

from nlp.medical_ner import extract_entities
from nlp.severity_parser import parse_severity
from nlp.language_detector import detect_language


def extract_symptoms(text: str, language: str = "auto") -> dict:
    if language == "auto":
        language = detect_language(text)

    entities = extract_entities(text, language)
    severity_info = parse_severity(text, language)

    return {
        "free_text_summary": text,
        "chief_complaint": entities.symptoms[0] if entities.symptoms else text[:80],
        "snomed_code": None,
        "onset": severity_info.onset or entities.onset_pattern,
        "duration_hours": severity_info.duration_hours,
        "pain_scale": severity_info.pain_scale,
        "severity": severity_info.level or entities.severity,
        "body_locations": entities.body_locations,
        "associated_symptoms": entities.associated,
        "triggers": entities.triggers,
        "relieving_factors": entities.relieving,
        "worsening_factors": entities.worsening,
        "medications": entities.medications,
        "medical_history": entities.medical_history,
        "vital_signs": entities.vital_signs,
        "symptoms": entities.symptoms,
    }
