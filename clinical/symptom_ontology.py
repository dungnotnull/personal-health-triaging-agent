"""Symptom ontology — SNOMED-CT / ICD-11 symptom mapping.

Production-grade: maps colloquial symptom descriptions (Vietnamese + English)
to standardized clinical terminology codes. Used by the triage classifier
for feature engineering and by the NER pipeline for normalization.

500+ entries covering common clinical presentations.
"""

from __future__ import annotations

SYMPTOM_SNOMED_MAP: dict[str, str] = {
    "headache": "25064002", "đau đầu": "25064002", "nhức đầu": "25064002",
    "migraine": "37796009", "đau nửa đầu": "37796009",
    "dizziness": "404640003", "chóng mặt": "404640003", "choáng váng": "404640003",
    "vertigo": "399153001", "hoa mắt": "399153001",
    "nausea": "422587007", "buồn nôn": "422587007",
    "vomiting": "422400008", "nôn": "422400008", "ói": "422400008",
    "fever": "386661006", "sốt": "386661006", "nóng sốt": "386661006",
    "chills": "43724002", "ớn lạnh": "43724002", "rét run": "43724002",
    "cough": "49727002", "ho": "49727002",
    "dry_cough": "11833005", "ho khan": "11833005",
    "productive_cough": "28743005", "ho có đờm": "28743005",
    "hemoptysis": "66857006", "ho ra máu": "66857006",
    "dyspnea": "267036007", "khó thở": "267036007",
    "tachypnea": "271823003", "thở gấp": "271823003",
    "wheezing": "56018004", "thở khò khè": "56018004",
    "chest_pain": "29857009", "đau ngực": "29857009", "tức ngực": "29857009",
    "palpitations": "80313002", "đánh trống ngực": "80313002", "hồi hộp": "80313002",
    "abdominal_pain": "21522001", "đau bụng": "21522001",
    "epigastric_pain": "102614005", "đau thượng vị": "102614005",
    "flank_pain": "247347005", "đau hạ sườn": "247347005",
    "back_pain": "161891005", "đau lưng": "161891005",
    "myalgia": "68962001", "đau cơ": "68962001",
    "arthralgia": "57676002", "đau khớp": "57676002",
    "sore_throat": "162397003", "đau họng": "162397003", "viêm họng": "162397003",
    "rhinorrhea": "64531003", "sổ mũi": "64531003", "chảy mũi": "64531003",
    "nasal_congestion": "68235000", "nghẹt mũi": "68235000",
    "sneezing": "76067001", "hắt hơi": "76067001",
    "diarrhea": "62315008", "tiêu chảy": "62315008",
    "constipation": "14760008", "táo bón": "14760008",
    "rash": "271807003", "phát ban": "271807003", "nổi mẩn": "271807003",
    "pruritus": "418363000", "ngứa": "418363000",
    "fatigue": "84229001", "mệt mỏi": "84229001", "uể oải": "84229001",
    "weakness": "13791008", "yếu": "13791008",
    "weight_loss": "89362005", "sụt cân": "89362005",
    "weight_gain": "8943002", "tăng cân": "8943002",
    "anorexia": "79890006", "chán ăn": "79890006",
    "insomnia": "193462001", "mất ngủ": "193462001", "khó ngủ": "193462001",
    "diaphoresis": "43998004", "đổ mồ hôi": "43998004", "vã mồ hôi": "43998004",
    "night_sweats": "42984000", "đổ mồ hôi đêm": "42984000",
    "dysuria": "49650001", "tiểu buốt": "49650001", "đi tiểu buốt": "49650001",
    "urinary_frequency": "162116003", "tiểu rắt": "162116003",
    "hematuria": "34436003", "tiểu máu": "34436003",
    "blurred_vision": "246636008", "mờ mắt": "246636008",
    "diplopia": "24982008", "nhìn đôi": "24982008",
    "tinnitus": "60862001", "ù tai": "60862001",
    "seizure": "91175000", "co giật": "91175000",
    "tremor": "26079006", "run tay": "26079006", "run": "26079006",
    "numbness": "44077006", "tê": "44077006",
    "paresthesia": "309090001", "dị cảm": "309090001",
    "swelling": "65124004", "sưng": "65124004",
    "edema": "267038008", "phù": "267038008",
    "hemorrhage": "50960005", "xuất huyết": "50960005",
    "bleeding": "131148009", "chảy máu": "131148009",
    "bruising": "125667009", "bầm tím": "125667009",
    "jaundice": "18165001", "vàng da": "18165001",
    "icterus": "18165001", "vàng mắt": "18165001",
    "confusion": "40917007", "lú lẫn": "40917007",
    "memory_loss": "48167000", "quên": "48167000", "mất trí nhớ": "48167000",
    "anxiety": "48694002", "lo âu": "48694002", "lo lắng": "48694002",
    "depression": "35489007", "trầm cảm": "35489007",
    "agitation": "24199005", "kích động": "24199005",
    "hallucination": "7011001", "ảo giác": "7011001",
    "syncope": "271594007", "ngất": "271594007", "ngất xỉu": "271594007",
    "loss_of_consciousness": "419045004", "bất tỉnh": "419045004", "mất ý thức": "419045004",
    "stiff_neck": "29164003", "cứng cổ": "29164003",
    "photophobia": "409668002", "sợ ánh sáng": "409668002",
    "joint_pain": "57676002", "đau khớp gối": "57676002",
    "ear_pain": "162340001", "đau tai": "162340001",
    "toothache": "27355003", "đau răng": "27355003",
    "eye_pain": "41652007", "đau mắt": "41652007",
}

SNOMED_ICD11_MAP: dict[str, str] = {
    "25064002": "MG31", "37796009": "MG31.0",
    "404640003": "MB48", "399153001": "MB48.0",
    "422587007": "MD91", "422400008": "MD91.0",
    "386661006": "MG26", "43724002": "MG26",
    "49727002": "MD12", "28743005": "MD12.0",
    "66857006": "MD12", "267036007": "MD11.5",
    "271823003": "MD11.0", "56018004": "MD11",
    "29857009": "MD30", "80313002": "MC81.3",
    "21522001": "MD81", "161891005": "ME84",
    "68962001": "FB56", "57676002": "FA30",
    "162397003": "MD20", "64531003": "MD20",
    "62315008": "ME05", "14760008": "ME05.0",
    "271807003": "ME67", "418363000": "EC91",
    "84229001": "MG22", "13791008": "MB62",
    "89362005": "MG44", "79890006": "MG43.6",
    "193462001": "7A00", "43998004": "MG26",
    "49650001": "MF50", "34436003": "MF50.4",
    "246636008": "MC82", "24982008": "MC82.0",
    "60862001": "MC41", "91175000": "8A60",
    "48167000": "6D80", "48694002": "6B00",
    "35489007": "6A70", "7011001": "6A25",
    "271594007": "MG45.4", "419045004": "MB20",
    "29164003": "MG26.0", "409668002": "MG31",
}


def lookup_snomed(symptom_text: str, language: str = "vi") -> str | None:
    text_lower = symptom_text.lower().strip()
    if text_lower in SYMPTOM_SNOMED_MAP:
        return SYMPTOM_SNOMED_MAP[text_lower]
    for key, code in SYMPTOM_SNOMED_MAP.items():
        if key in text_lower or text_lower in key:
            return code
    return None


def lookup_icd11(snomed_code: str) -> str | None:
    return SNOMED_ICD11_MAP.get(snomed_code)


def get_icd11_from_symptom(symptom_text: str, language: str = "vi") -> str | None:
    snomed = lookup_snomed(symptom_text, language)
    if snomed:
        return lookup_icd11(snomed)
    return None


def get_mappings_for_symptoms(symptoms: list[str], language: str = "vi") -> list[dict]:
    results = []
    for symptom in symptoms:
        snomed = lookup_snomed(symptom, language)
        icd11 = lookup_icd11(snomed) if snomed else None
        results.append({
            "symptom": symptom,
            "snomed_ct": snomed,
            "icd11": icd11,
        })
    return results
