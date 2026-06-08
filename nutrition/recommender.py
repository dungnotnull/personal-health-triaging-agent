"""Condition-based nutrition recommendation engine.

Production-grade: provides culturally relevant dietary guidance
for specific symptoms and conditions. Vietnam-first with English fallback.
Integrates with food_db for lookup and meal_planner for menus.
"""

from __future__ import annotations

from typing import Any

CONDITION_NUTRITION_MAP: dict[str, dict[str, Any]] = {
    "fever": {
        "recommended_vi": ["cháo trắng", "súp gà", "nước cam", "trà gừng", "dừa tươi", "canh rau ngót", "nước chanh ấm mật ong"],
        "recommended_en": ["rice congee", "chicken soup", "orange juice", "ginger tea", "coconut water", "leafy green soup", "warm lemon water with honey"],
        "avoid_vi": ["đồ chiên xào", "rượu bia", "đồ lạnh", "nước đá", "đồ cay nóng"],
        "avoid_en": ["fried foods", "alcohol", "cold beverages", "ice water", "spicy foods"],
        "nutrients_focus": ["vitamin C", "zinc", "electrolytes", "fluid", "easy-digest-protein"],
        "hydration_liters": 2.5,
        "meal_frequency": "small_frequent",
    },
    "headache": {
        "recommended_vi": ["nước lọc", "trà gừng", "chuối", "cơm trắng", "cá hấp", "rau xanh"],
        "recommended_en": ["water", "ginger tea", "banana", "steamed rice", "steamed fish", "leafy greens"],
        "avoid_vi": ["cà phê", "rượu bia", "đồ ngọt nhiều đường", "bột ngọt nhiều", "phô mai già"],
        "avoid_en": ["coffee", "alcohol", "high-sugar foods", "MSG-rich foods", "aged cheese"],
        "nutrients_focus": ["magnesium", "vitamin B2", "water", "omega-3"],
        "hydration_liters": 2.5,
        "meal_frequency": "regular",
    },
    "cough": {
        "recommended_vi": ["mật ong chanh", "trà gừng", "cháo trắng", "súp gà", "nước ấm", "tỏi"],
        "recommended_en": ["honey with lemon", "ginger tea", "rice congee", "chicken soup", "warm water", "garlic"],
        "avoid_vi": ["đồ lạnh", "đồ chiên xào", "sữa và chế phẩm sữa", "đồ ngọt"],
        "avoid_en": ["cold items", "fried foods", "dairy products", "sweets"],
        "nutrients_focus": ["vitamin C", "zinc", "antioxidants", "fluid"],
        "hydration_liters": 2.0,
        "meal_frequency": "small_frequent",
    },
    "abdominal_pain": {
        "recommended_vi": ["cháo trắng", "cơm trắng", "chuối", "bánh mì nướng", "khoai lang luộc", "sữa chua"],
        "recommended_en": ["rice congee", "steamed rice", "banana", "toast", "boiled sweet potato", "yogurt"],
        "avoid_vi": ["đồ chiên xào", "đồ cay", "rượu bia", "cà phê", "sữa tươi", "đồ nhiều dầu mỡ"],
        "avoid_en": ["fried foods", "spicy foods", "alcohol", "coffee", "milk", "fatty foods"],
        "nutrients_focus": ["easy-digest-carbs", "potassium", "probiotics", "fluid"],
        "hydration_liters": 2.0,
        "meal_frequency": "small_frequent",
    },
    "respiratory_infection": {
        "recommended_vi": ["tỏi", "gừng", "mật ong", "chanh", "cháo", "súp gà", "nước cam", "trà xanh"],
        "recommended_en": ["garlic", "ginger", "honey", "lemon", "congee", "chicken soup", "orange juice", "green tea"],
        "avoid_vi": ["đồ lạnh", "đồ chiên xào", "rượu bia", "thuốc lá"],
        "avoid_en": ["cold items", "fried foods", "alcohol", "tobacco"],
        "nutrients_focus": ["vitamin C", "vitamin D", "zinc", "fluid", "antioxidants"],
        "hydration_liters": 2.5,
        "meal_frequency": "small_frequent",
    },
    "fatigue": {
        "recommended_vi": ["chuối", "trứng luộc", "cá hấp", "khoai lang", "rau xanh", "đậu xanh", "nước dừa"],
        "recommended_en": ["banana", "boiled egg", "steamed fish", "sweet potato", "leafy greens", "mung beans", "coconut water"],
        "avoid_vi": ["cà phê nhiều", "đồ ngọt", "đồ chiên xào", "rượu bia"],
        "avoid_en": ["excess coffee", "sweets", "fried foods", "alcohol"],
        "nutrients_focus": ["iron", "vitamin B12", "magnesium", "complex-carbs", "protein"],
        "hydration_liters": 2.0,
        "meal_frequency": "regular",
    },
    "hypertension": {
        "recommended_vi": ["rau xanh", "cá hấp", "chuối", "khoai lang", "đậu phụ", "tỏi", "trà xanh"],
        "recommended_en": ["leafy greens", "steamed fish", "banana", "sweet potato", "tofu", "garlic", "green tea"],
        "avoid_vi": ["muối", "mắm", "đồ đóng hộp", "nội tạng", "rượu bia", "mỡ động vật"],
        "avoid_en": ["salt", "fish sauce", "canned foods", "organ meats", "alcohol", "animal fat"],
        "nutrients_focus": ["potassium", "magnesium", "omega-3", "fiber"],
        "sodium_limit_mg": 1500,
        "hydration_liters": 2.0,
        "meal_frequency": "regular",
    },
    "diabetes": {
        "recommended_vi": ["rau xanh", "cá", "đậu phụ", "gạo lứt", "khoai lang", "chuối xanh"],
        "recommended_en": ["leafy greens", "fish", "tofu", "brown rice", "sweet potato", "green banana"],
        "avoid_vi": ["đồ ngọt", "cơm trắng nhiều", "bánh mì trắng", "nước ngọt", "trái cây ngọt"],
        "avoid_en": ["sweets", "white rice excess", "white bread", "sugary drinks", "sweet fruits"],
        "nutrients_focus": ["fiber", "chromium", "magnesium", "low-GI-carbs"],
        "hydration_liters": 2.0,
        "meal_frequency": "regular_small",
    },
    "default": {
        "recommended_vi": ["cơm trắng", "rau xanh", "cá", "thịt nạc", "trái cây", "nước lọc"],
        "recommended_en": ["rice", "leafy greens", "fish", "lean meat", "fruit", "water"],
        "avoid_vi": ["rượu bia", "đồ chiên xào nhiều", "đồ ngọt nhiều"],
        "avoid_en": ["alcohol", "excess fried foods", "excess sweets"],
        "nutrients_focus": ["balanced", "vitamin C", "protein", "fiber"],
        "hydration_liters": 2.0,
        "meal_frequency": "regular",
    },
}


def get_recommendations(condition: str, language: str = "vi") -> dict[str, Any]:
    condition_key = condition.lower().replace(" ", "_").replace("-", "_")
    mapping = CONDITION_NUTRITION_MAP.get(condition_key, CONDITION_NUTRITION_MAP["default"])

    rec_key = "recommended_vi" if language == "vi" else "recommended_en"
    avoid_key = "avoid_vi" if language == "vi" else "avoid_en"

    return {
        "recommended": mapping.get(rec_key, mapping.get("recommended_en", [])),
        "avoid": mapping.get(avoid_key, mapping.get("avoid_en", [])),
        "nutrients_focus": mapping.get("nutrients_focus", []),
        "hydration_liters": mapping.get("hydration_liters", 2.0),
        "meal_frequency": mapping.get("meal_frequency", "regular"),
        "sodium_limit_mg": mapping.get("sodium_limit_mg"),
    }


def get_condition_keywords(condition: str, language: str = "vi") -> str:
    recs = get_recommendations(condition, language)
    lines = []
    lines.append("**Recommended foods:** " + ", ".join(recs["recommended"][:6]))
    if recs["avoid"]:
        lines.append("**Foods to avoid:** " + ", ".join(recs["avoid"][:5]))
    lines.append(f"**Hydration:** At least {recs['hydration_liters']}L of water per day")
    if recs.get("sodium_limit_mg"):
        lines.append(f"**Sodium limit:** Max {recs['sodium_limit_mg']}mg per day")
    return "\n".join(lines)
