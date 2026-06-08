"""Meal plan generator — 3-day condition-appropriate Vietnamese meal plans.

Vietnam-first: generates culturally appropriate meal plans based on
the user's condition, dietary preferences, allergies, and language.
"""

from __future__ import annotations

from typing import Any

from nutrition.recommender import get_recommendations
from nutrition.food_db import lookup_food

_MEAL_TEMPLATES_VI: dict[str, list[dict[str, Any]]] = {
    "fever": [
        {"meal": "Sáng", "items": ["cháo trắng", "nước cam"], "notes": "Ăn ấm, chia nhỏ bữa"},
        {"meal": "Trưa", "items": ["súp gà", "cơm trắng ít", "canh rau ngót"], "notes": "Uống nhiều nước giữa các bữa"},
        {"meal": "Tối", "items": ["cháo trắng", "trứng luộc"], "notes": "Ăn nhẹ trước khi ngủ"},
    ],
    "headache": [
        {"meal": "Sáng", "items": ["bánh mì", "trứng luộc", "chuối"], "notes": "Uống 1 ly nước ấm"},
        {"meal": "Trưa", "items": ["cơm trắng", "cá hấp", "rau muống xào tỏi"], "notes": "Tránh cà phê, trà đặc"},
        {"meal": "Tối", "items": ["cơm trắng", "đậu phụ sốt cà chua", "canh rau ngót"], "notes": "Nghỉ ngơi trong phòng tối yên tĩnh"},
    ],
    "cough": [
        {"meal": "Sáng", "items": ["cháo trắng", "mật ong chanh"], "notes": "Uống nước ấm"},
        {"meal": "Trưa", "items": ["súp gà", "bánh mì nướng"], "notes": "Thêm tỏi vào món ăn"},
        {"meal": "Tối", "items": ["cháo trắng", "trà gừng mật ong"], "notes": "Tránh đồ lạnh"},
    ],
    "abdominal_pain": [
        {"meal": "Sáng", "items": ["cháo trắng", "chuối"], "notes": "Ăn chậm, nhai kỹ"},
        {"meal": "Trưa", "items": ["cơm trắng", "cá hấp", "khoai lang luộc"], "notes": "Tránh dầu mỡ"},
        {"meal": "Tối", "items": ["cháo trắng", "sữa chua"], "notes": "Ăn nhẹ, không ăn quá no"},
    ],
    "default": [
        {"meal": "Sáng", "items": ["bánh mì", "trứng luộc", "chuối"], "notes": "Uống đủ nước"},
        {"meal": "Trưa", "items": ["cơm trắng", "thịt kho tàu", "rau muống xào tỏi"], "notes": "Ăn điều độ"},
        {"meal": "Tối", "items": ["cơm trắng", "cá hấp", "canh chua"], "notes": "Ăn nhẹ buổi tối"},
    ],
}

_MEAL_TEMPLATES_EN: dict[str, list[dict[str, Any]]] = {
    "fever": [
        {"meal": "Breakfast", "items": ["rice congee", "orange juice"], "notes": "Eat warm, small frequent meals"},
        {"meal": "Lunch", "items": ["chicken soup", "rice", "leafy green soup"], "notes": "Drink water between meals"},
        {"meal": "Dinner", "items": ["rice congee", "boiled egg"], "notes": "Light meal before bed"},
    ],
    "headache": [
        {"meal": "Breakfast", "items": ["bread", "boiled egg", "banana"], "notes": "Drink warm water"},
        {"meal": "Lunch", "items": ["rice", "steamed fish", "stir-fried water spinach"], "notes": "Avoid coffee, strong tea"},
        {"meal": "Dinner", "items": ["rice", "tofu in tomato sauce", "leafy green soup"], "notes": "Rest in dark quiet room"},
    ],
    "cough": [
        {"meal": "Breakfast", "items": ["rice congee", "honey with lemon"], "notes": "Drink warm water"},
        {"meal": "Lunch", "items": ["chicken soup", "toast"], "notes": "Add garlic to meals"},
        {"meal": "Dinner", "items": ["rice congee", "ginger tea with honey"], "notes": "Avoid cold items"},
    ],
    "abdominal_pain": [
        {"meal": "Breakfast", "items": ["rice congee", "banana"], "notes": "Eat slowly, chew well"},
        {"meal": "Lunch", "items": ["rice", "steamed fish", "boiled sweet potato"], "notes": "Avoid fatty foods"},
        {"meal": "Dinner", "items": ["rice congee", "yogurt"], "notes": "Light meal, avoid overeating"},
    ],
    "default": [
        {"meal": "Breakfast", "items": ["bread", "boiled egg", "banana"], "notes": "Stay hydrated"},
        {"meal": "Lunch", "items": ["rice", "braised pork with eggs", "stir-fried water spinach"], "notes": "Eat moderately"},
        {"meal": "Dinner", "items": ["rice", "steamed fish", "sour soup"], "notes": "Light dinner"},
    ],
}


def generate_meal_plan(
    condition: str,
    days: int = 3,
    allergies: list[str] | None = None,
    language: str = "vi",
) -> list[dict[str, Any]]:
    condition_key = condition.lower().replace(" ", "_").replace("-", "_")
    templates = _MEAL_TEMPLATES_VI if language == "vi" else _MEAL_TEMPLATES_EN
    template = templates.get(condition_key, templates["default"])
    recs = get_recommendations(condition, language)

    snacks_vi = {
        "morning": ["chuối", "nước cam"],
        "afternoon": ["sữa chua", "khoai lang luộc"],
        "evening": ["trà gừng", "nước ấm mật ong"],
    }
    snacks_en = {
        "morning": ["banana", "orange juice"],
        "afternoon": ["yogurt", "boiled sweet potato"],
        "evening": ["ginger tea", "warm honey water"],
    }
    snacks = snacks_vi if language == "vi" else snacks_en

    plan = []
    for day in range(1, days + 1):
        day_plan = {
            "day": day,
            "meals": [],
            "hydration_goal": f"{recs['hydration_liters']}L",
            "nutrition_focus": recs["nutrients_focus"],
        }
        for i, meal_tmpl in enumerate(template):
            day_plan["meals"].append({
                "meal": meal_tmpl["meal"],
                "items": meal_tmpl["items"],
                "notes": meal_tmpl["notes"],
            })
            if i == 0:
                day_plan["meals"].append({
                    "meal": "Giữa buổi" if language == "vi" else "Mid-morning",
                    "items": snacks["morning"],
                    "notes": "Ăn nhẹ giữa buổi" if language == "vi" else "Light snack",
                })
            elif i == 1:
                day_plan["meals"].append({
                    "meal": "Xế chiều" if language == "vi" else "Afternoon",
                    "items": snacks["afternoon"],
                    "notes": "Ăn nhẹ buổi chiều" if language == "vi" else "Afternoon snack",
                })
        plan.append(day_plan)

    if allergies:
        for day_plan in plan:
            for meal in day_plan["meals"]:
                meal["items"] = [item for item in meal["items"] if item not in allergies]

    return plan
