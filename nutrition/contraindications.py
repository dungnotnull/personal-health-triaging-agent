"""Food-condition and food-medication contraindication checker.

Production-grade: warns users about dangerous food-condition and
food-medication interactions. Vietnam-first food vocabulary.
"""

from __future__ import annotations

from typing import Any

CONTRAINDICATIONS: list[dict[str, Any]] = [
    {
        "id": "CI_001",
        "condition": "hypertension",
        "foods_vi": ["mắm", "nước mắm", "muối", "đồ hộp", "đồ muối chua"],
        "foods_en": ["fish sauce", "salt", "canned foods", "pickled foods"],
        "risk": "high_sodium",
        "severity": "warning",
        "message_vi": "Thực phẩm nhiều muối có thể làm tăng huyết áp",
        "message_en": "High-sodium foods can increase blood pressure",
    },
    {
        "id": "CI_002",
        "condition": "diabetes",
        "foods_vi": ["bánh ngọt", "nước ngọt", "kẹo", "cơm trắng nhiều", "chè"],
        "foods_en": ["cake", "soda", "candy", "white rice excess", "sweet desserts"],
        "risk": "hyperglycemia",
        "severity": "warning",
        "message_vi": "Thực phẩm nhiều đường có thể làm tăng đường huyết",
        "message_en": "High-sugar foods can increase blood glucose",
    },
    {
        "id": "CI_003",
        "condition": "gout",
        "foods_vi": ["nội tạng", "hải sản", "thịt đỏ", "bia rượu", "đậu"],
        "foods_en": ["organ meats", "seafood", "red meat", "beer", "legumes"],
        "risk": "hyperuricemia",
        "severity": "danger",
        "message_vi": "Thực phẩm giàu purine có thể gây cơn gout cấp",
        "message_en": "Purine-rich foods can trigger acute gout attack",
    },
    {
        "id": "CI_004",
        "condition": "fever",
        "foods_vi": ["rượu bia", "đồ lạnh", "nước đá"],
        "foods_en": ["alcohol", "cold foods", "ice water"],
        "risk": "dehydration_worsening",
        "severity": "warning",
        "message_vi": "Đồ lạnh và rượu bia có thể làm tình trạng sốt nặng hơn",
        "message_en": "Cold items and alcohol can worsen fever",
    },
    {
        "id": "CI_005",
        "condition": "abdominal_pain",
        "foods_vi": ["đồ cay", "đồ chiên xào", "cà phê", "sữa tươi", "rượu bia"],
        "foods_en": ["spicy foods", "fried foods", "coffee", "milk", "alcohol"],
        "risk": "irritation",
        "severity": "warning",
        "message_vi": "Thực phẩm cay nóng và dầu mỡ có thể kích thích dạ dày",
        "message_en": "Spicy and fatty foods can irritate the stomach",
    },
    {
        "id": "CI_006",
        "condition": "pregnancy",
        "foods_vi": ["rau ngót sống", "đu đủ xanh", "rượu bia", "cá sống", "thuốc lá"],
        "foods_en": ["raw katuk", "green papaya", "alcohol", "raw fish", "tobacco"],
        "risk": "pregnancy_complication",
        "severity": "danger",
        "message_vi": "Thực phẩm này có thể gây nguy hiểm cho thai kỳ",
        "message_en": "These foods can be dangerous during pregnancy",
    },
    {
        "id": "CI_007",
        "condition": "liver_disease",
        "foods_vi": ["rượu bia", "đồ chiên xào", "nội tạng", "thuốc lá"],
        "foods_en": ["alcohol", "fried foods", "organ meats", "tobacco"],
        "risk": "liver_damage",
        "severity": "danger",
        "message_vi": "Rượu bia và đồ chiên xào gây hại cho gan",
        "message_en": "Alcohol and fried foods damage the liver",
    },
    {
        "id": "CI_008",
        "condition": "kidney_disease",
        "foods_vi": ["muối", "mắm", "đồ hộp", "chuối nhiều", "khoai tây"],
        "foods_en": ["salt", "fish sauce", "canned foods", "bananas excess", "potatoes"],
        "risk": "electrolyte_imbalance",
        "severity": "danger",
        "message_vi": "Hạn chế natri và kali nếu có bệnh thận",
        "message_en": "Limit sodium and potassium with kidney disease",
    },
    {
        "id": "CI_009",
        "condition": "asthma",
        "foods_vi": ["đồ lạnh", "tôm", "cua", "đồ muối chua", "rượu bia"],
        "foods_en": ["cold items", "shrimp", "crab", "pickled foods", "alcohol"],
        "risk": "asthma_trigger",
        "severity": "warning",
        "message_vi": "Thực phẩm này có thể kích hoạt cơn hen",
        "message_en": "These foods may trigger asthma attacks",
    },
    {
        "id": "CI_010",
        "condition": "allergy_common",
        "foods_vi": ["tôm", "cua", "đậu phộng", "trứng", "sữa", "hải sản"],
        "foods_en": ["shrimp", "crab", "peanuts", "eggs", "milk", "seafood"],
        "risk": "allergic_reaction",
        "severity": "danger",
        "message_vi": "Dị ứng thực phẩm phổ biến — tránh nếu có tiền sử",
        "message_en": "Common food allergens — avoid if you have a history",
    },
]

_MEDICATION_INTERACTIONS: list[dict[str, Any]] = [
    {"medication": "warfarin", "foods_vi": ["rau xanh đậm", "bông cải", "cải xoăn"], "foods_en": ["dark leafy greens", "broccoli", "kale"], "risk": "vitamin_k_interference", "message_vi": "Thực phẩm giàu vitamin K có thể giảm tác dụng của thuốc chống đông", "message_en": "Vitamin K-rich foods can reduce anticoagulant effect"},
    {"medication": "thuốc hạ huyết áp", "foods_vi": ["chuối", "khoai tây"], "foods_en": ["bananas", "potatoes"], "risk": "hyperkalemia", "message_vi": "Thực phẩm giàu kali có thể ảnh hưởng đến huyết áp", "message_en": "Potassium-rich foods can affect blood pressure medication"},
    {"medication": "kháng sinh", "foods_vi": ["sữa", "sữa chua"], "foods_en": ["milk", "yogurt"], "risk": "reduced_absorption", "message_vi": "Sữa có thể giảm hấp thu kháng sinh — uống cách 2 giờ", "message_en": "Dairy can reduce antibiotic absorption — take 2 hours apart"},
]


def check_contraindications(condition: str, foods: list[str], language: str = "vi") -> list[dict[str, Any]]:
    condition_key = condition.lower().replace(" ", "_").replace("-", "_")
    results = []
    for ci in CONTRAINDICATIONS:
        if ci["condition"] == condition_key:
            food_key = "foods_vi" if language == "vi" else "foods_en"
            matched = [f for f in foods if any(fi in f.lower() for fi in ci[food_key])]
            if matched:
                results.append({
                    "foods": matched,
                    "risk": ci["risk"],
                    "severity": ci["severity"],
                    "message": ci.get(f"message_{language}", ci.get("message_en", "")),
                })
    return results


def check_medication_interactions(medications: list[str], foods: list[str], language: str = "vi") -> list[dict[str, Any]]:
    results = []
    for mi in _MEDICATION_INTERACTIONS:
        med_name = mi["medication"].lower()
        if any(med_name in m.lower() for m in medications):
            food_key = "foods_vi" if language == "vi" else "foods_en"
            matched = [f for f in foods if any(fi in f.lower() for fi in mi[food_key])]
            if matched:
                results.append({
                    "medication": mi["medication"],
                    "foods": matched,
                    "risk": mi["risk"],
                    "message": mi.get(f"message_{language}", mi.get("message_en", "")),
                })
    return results
