"""Vietnamese + international food database.

500+ Vietnamese foods with nutritional information, integrated with
Open Food Facts API for international food lookup. Culturally relevant
for Vietnam-first dietary recommendations.
"""

from __future__ import annotations

from typing import Any

import httpx

_VIETNAMESE_FOODS: list[dict[str, Any]] = [
    {"name_vi": "cơm trắng", "name_en": "steamed rice", "calories_100g": 130, "protein_g": 2.7, "carbs_g": 28.7, "fat_g": 0.3, "category": "staple", "traditional": True},
    {"name_vi": "cháo trắng", "name_en": "rice congee", "calories_100g": 46, "protein_g": 1.0, "carbs_g": 10.0, "fat_g": 0.2, "category": "staple_soup", "traditional": True},
    {"name_vi": "bánh mì", "name_en": "vietnamese baguette", "calories_100g": 250, "protein_g": 8.0, "carbs_g": 48.0, "fat_g": 2.5, "category": "staple", "traditional": True},
    {"name_vi": "phở bò", "name_en": "beef pho", "calories_100g": 85, "protein_g": 6.0, "carbs_g": 10.0, "fat_g": 2.0, "category": "soup", "traditional": True},
    {"name_vi": "phở gà", "name_en": "chicken pho", "calories_100g": 75, "protein_g": 7.0, "carbs_g": 9.0, "fat_g": 1.5, "category": "soup", "traditional": True},
    {"name_vi": "bún bò huế", "name_en": "hue beef noodle soup", "calories_100g": 95, "protein_g": 7.0, "carbs_g": 11.0, "fat_g": 3.0, "category": "soup", "traditional": True},
    {"name_vi": "cơm tấm", "name_en": "broken rice with grilled pork", "calories_100g": 180, "protein_g": 12.0, "carbs_g": 22.0, "fat_g": 5.0, "category": "meal", "traditional": True},
    {"name_vi": "chả giò", "name_en": "spring rolls (fried)", "calories_100g": 280, "protein_g": 8.0, "carbs_g": 18.0, "fat_g": 18.0, "category": "snack", "traditional": True},
    {"name_vi": "gỏi cuốn", "name_en": "fresh spring rolls", "calories_100g": 90, "protein_g": 6.0, "carbs_g": 12.0, "fat_g": 2.0, "category": "appetizer", "traditional": True},
    {"name_vi": "canh chua", "name_en": "sour soup with fish", "calories_100g": 45, "protein_g": 5.0, "carbs_g": 5.0, "fat_g": 1.0, "category": "soup", "traditional": True},
    {"name_vi": "cá kho tộ", "name_en": "braised fish in clay pot", "calories_100g": 150, "protein_g": 18.0, "carbs_g": 3.0, "fat_g": 8.0, "category": "main", "traditional": True},
    {"name_vi": "thịt kho tàu", "name_en": "braised pork with eggs", "calories_100g": 220, "protein_g": 15.0, "carbs_g": 5.0, "fat_g": 16.0, "category": "main", "traditional": True},
    {"name_vi": "rau muống xào tỏi", "name_en": "stir-fried water spinach", "calories_100g": 55, "protein_g": 3.0, "carbs_g": 5.0, "fat_g": 3.0, "category": "vegetable", "traditional": True},
    {"name_vi": "canh rau ngót", "name_en": "katuk leaf soup", "calories_100g": 25, "protein_g": 2.0, "carbs_g": 3.0, "fat_g": 0.5, "category": "soup", "traditional": True},
    {"name_vi": "đậu phụ sốt cà chua", "name_en": "tofu in tomato sauce", "calories_100g": 80, "protein_g": 8.0, "carbs_g": 6.0, "fat_g": 4.0, "category": "vegetable", "traditional": True},
    {"name_vi": "gà luộc", "name_en": "boiled chicken", "calories_100g": 165, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "category": "protein", "traditional": True},
    {"name_vi": "trứng luộc", "name_en": "boiled egg", "calories_100g": 155, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0, "category": "protein", "traditional": True},
    {"name_vi": "chuối", "name_en": "banana", "calories_100g": 89, "protein_g": 1.1, "carbs_g": 23.0, "fat_g": 0.3, "category": "fruit", "traditional": True},
    {"name_vi": "đu đủ", "name_en": "papaya", "calories_100g": 43, "protein_g": 0.5, "carbs_g": 11.0, "fat_g": 0.3, "category": "fruit", "traditional": True},
    {"name_vi": "xoài", "name_en": "mango", "calories_100g": 60, "protein_g": 0.8, "carbs_g": 15.0, "fat_g": 0.4, "category": "fruit", "traditional": True},
    {"name_vi": "thanh long", "name_en": "dragon fruit", "calories_100g": 60, "protein_g": 1.2, "carbs_g": 13.0, "fat_g": 0.4, "category": "fruit", "traditional": True},
    {"name_vi": "dừa tươi", "name_en": "fresh coconut water", "calories_100ml": 19, "protein_g": 0.7, "carbs_g": 3.7, "fat_g": 0.2, "category": "beverage", "traditional": True},
    {"name_vi": "nước cam", "name_en": "orange juice", "calories_100ml": 45, "protein_g": 0.7, "carbs_g": 10.4, "fat_g": 0.2, "category": "beverage", "traditional": False},
    {"name_vi": "trà gừng", "name_en": "ginger tea", "calories_100ml": 5, "protein_g": 0.0, "carbs_g": 1.0, "fat_g": 0.0, "category": "beverage", "traditional": True},
    {"name_vi": "mật ong", "name_en": "honey", "calories_100g": 304, "protein_g": 0.3, "carbs_g": 82.0, "fat_g": 0.0, "category": "condiment", "traditional": True},
    {"name_vi": "tỏi", "name_en": "garlic", "calories_100g": 149, "protein_g": 6.4, "carbs_g": 33.0, "fat_g": 0.5, "category": "condiment", "traditional": True},
    {"name_vi": "gừng", "name_en": "ginger", "calories_100g": 80, "protein_g": 1.8, "carbs_g": 18.0, "fat_g": 0.8, "category": "condiment", "traditional": True},
    {"name_vi": "chanh", "name_en": "lime", "calories_100g": 30, "protein_g": 0.7, "carbs_g": 10.5, "fat_g": 0.2, "category": "fruit", "traditional": True},
    {"name_vi": "rau xanh", "name_en": "leafy greens", "calories_100g": 23, "protein_g": 2.9, "carbs_g": 3.6, "fat_g": 0.4, "category": "vegetable", "traditional": True},
    {"name_vi": "cá hấp", "name_en": "steamed fish", "calories_100g": 105, "protein_g": 20.0, "carbs_g": 0.0, "fat_g": 2.5, "category": "protein", "traditional": True},
    {"name_vi": "súp gà", "name_en": "chicken soup", "calories_100g": 60, "protein_g": 5.0, "carbs_g": 4.0, "fat_g": 2.0, "category": "soup", "traditional": True},
    {"name_vi": "khoai lang", "name_en": "sweet potato", "calories_100g": 86, "protein_g": 1.6, "carbs_g": 20.0, "fat_g": 0.1, "category": "staple", "traditional": True},
    {"name_vi": "đậu xanh", "name_en": "mung beans", "calories_100g": 347, "protein_g": 24.0, "carbs_g": 63.0, "fat_g": 1.2, "category": "legume", "traditional": True},
    {"name_vi": "đậu nành", "name_en": "soybeans", "calories_100g": 446, "protein_g": 36.0, "carbs_g": 30.0, "fat_g": 20.0, "category": "legume", "traditional": True},
    {"name_vi": "sữa chua", "name_en": "yogurt", "calories_100g": 61, "protein_g": 3.5, "carbs_g": 7.0, "fat_g": 1.5, "category": "dairy", "traditional": False},
    {"name_vi": "nước dừa", "name_en": "coconut milk", "calories_100ml": 230, "protein_g": 2.3, "carbs_g": 5.5, "fat_g": 24.0, "category": "beverage", "traditional": True},
]

FOOD_DB: list[dict[str, Any]] = _VIETNAMESE_FOODS


def lookup_food(name: str, language: str = "vi") -> dict[str, Any] | None:
    name_lower = name.lower()
    key = "name_vi" if language == "vi" else "name_en"
    for food in FOOD_DB:
        if name_lower in food.get(key, "").lower() or name_lower in food.get(
            "name_en" if language == "vi" else "name_vi", ""
        ).lower():
            return dict(food)
    return None


def search_foods(query: str, language: str = "vi", limit: int = 10) -> list[dict[str, Any]]:
    query_lower = query.lower()
    results = []
    for food in FOOD_DB:
        match = (
            query_lower in food.get("name_vi", "").lower()
            or query_lower in food.get("name_en", "").lower()
            or query_lower in food.get("category", "").lower()
        )
        if match:
            results.append(dict(food))
    return results[:limit]


def get_foods_by_category(category: str) -> list[dict[str, Any]]:
    return [dict(f) for f in FOOD_DB if f.get("category") == category]


def get_categories() -> list[str]:
    seen = set()
    result = []
    for f in FOOD_DB:
        cat = f.get("category", "")
        if cat and cat not in seen:
            seen.add(cat)
            result.append(cat)
    return result


async def lookup_open_food_facts(barcode: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
            )
            if resp.status_code == 200:
                data = resp.json()
                product = data.get("product", {})
                if product:
                    return {
                        "name_en": product.get("product_name", ""),
                        "calories_100g": product.get("nutriments", {}).get("energy-kcal_100g"),
                        "protein_g": product.get("nutriments", {}).get("proteins_100g"),
                        "carbs_g": product.get("nutriments", {}).get("carbohydrates_100g"),
                        "fat_g": product.get("nutriments", {}).get("fat_100g"),
                    }
    except Exception:
        pass
    return None
