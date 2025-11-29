# nutrition_api.py
import requests
from typing import Dict, Optional

# Local nutrition database (kept as-is for fast lookups)
LOCAL_NUTRITION_DB: Dict[str, Dict] = {
    "pizza": {
        "calories": 285,
        "protein": 12,
        "carbs": 36,
        "fat": 10,
        "fiber": 2,
        "vitamins": {"Vit A": "10%", "Vit C": "0%", "Vit B12": "15%"},
        "minerals": {"Calcium": "18%", "Iron": "10%", "Sodium": "25%"},
    },
    "burger": {
        "calories": 295,
        "protein": 17,
        "carbs": 30,
        "fat": 13,
        "fiber": 1,
        "vitamins": {"Vit B12": "30%", "Vit B6": "20%", "Vit A": "6%"},
        "minerals": {"Iron": "20%", "Zinc": "15%", "Sodium": "23%"},
    },
    "idli": {
        "calories": 60,
        "protein": 2,
        "carbs": 12,
        "fat": 0.4,
        "fiber": 0.6,
        "vitamins": {"Vit B1": "5%", "Vit B2": "4%", "Folate": "6%"},
        "minerals": {"Iron": "2%", "Calcium": "2%", "Potassium": "2%"},
    },
    "dosa": {
        "calories": 168,
        "protein": 4,
        "carbs": 27,
        "fat": 4.5,
        "fiber": 1.5,
        "vitamins": {"Vit B1": "5%", "Vit B2": "5%", "Folate": "6%"},
        "minerals": {"Iron": "5%", "Calcium": "3%", "Sodium": "4%"},
    },
    "biryani": {
        "calories": 350,
        "protein": 12,
        "carbs": 45,
        "fat": 12,
        "fiber": 2.5,
        "vitamins": {"Vit A": "5%", "Vit B12": "10%", "Vit C": "4%"},
        "minerals": {"Iron": "10%", "Sodium": "18%", "Potassium": "8%"},
    },
    "paneer butter masala": {
        "calories": 400,
        "protein": 15,
        "carbs": 20,
        "fat": 28,
        "fiber": 2,
        "vitamins": {"Vit A": "15%", "Vit B12": "20%", "Vit D": "10%"},
        "minerals": {"Calcium": "25%", "Iron": "6%", "Sodium": "12%"},
    },
    "salad": {
        "calories": 80,
        "protein": 2,
        "carbs": 12,
        "fat": 3,
        "fiber": 3,
        "vitamins": {"Vit A": "60%", "Vit C": "40%", "Vit K": "70%"},
        "minerals": {"Potassium": "8%", "Calcium": "4%", "Iron": "6%"},
    },
    "rice": {
        "calories": 200,
        "protein": 4,
        "carbs": 44,
        "fat": 0.4,
        "fiber": 0.6,
        "vitamins": {"Vit B1": "12%", "Vit B3": "15%", "Folate": "8%"},
        "minerals": {"Iron": "2%", "Magnesium": "5%", "Selenium": "15%"},
    },
    "roti": {
        "calories": 110,
        "protein": 3,
        "carbs": 20,
        "fat": 2,
        "fiber": 2,
        "vitamins": {"Vit B1": "5%", "Vit B3": "6%", "Folate": "4%"},
        "minerals": {"Iron": "4%", "Magnesium": "6%", "Potassium": "2%"},
    },
}


def _normalize(food_name: str) -> str:
    """Normalize food name for matching"""
    return food_name.strip().lower()


def _lookup_local(food_name: str) -> Optional[Dict]:
    """Search local database first"""
    key = _normalize(food_name)
    if key in LOCAL_NUTRITION_DB:
        return LOCAL_NUTRITION_DB[key]
    for k, v in LOCAL_NUTRITION_DB.items():
        if key in k or k in key:
            return v
    return None


def _fetch_from_openfoodfacts(food_name: str) -> Optional[Dict]:
    """
    Fetch nutrition data from Open Food Facts API (FREE - no API key needed!)
    """
    try:
        headers = {
            'User-Agent': 'scanEat/1.0 (workforsunil0@gmail.com)' 
        }
        
        # Search for the food product
        search_url = f"https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            'search_terms': food_name,
            'search_simple': 1,
            'action': 'process',
            'json': 1,
            'page_size': 1
        }
        
        resp = requests.get(search_url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Check if we got results
        if not data.get('products') or len(data['products']) == 0:
            return None
        
        product = data['products'][0]
        nutriments = product.get('nutriments', {})
        
        # Extract nutrition per 100g
        def get_nutrient(key: str, default: float = 0.0) -> float:
            return float(nutriments.get(f"{key}_100g", default))
        
        calories = int(get_nutrient('energy-kcal'))
        protein = get_nutrient('proteins')
        carbs = get_nutrient('carbohydrates')
        fat = get_nutrient('fat')
        fiber = get_nutrient('fiber')
        
        # Vitamins (if available)
        vitamins = {}
        vit_a = get_nutrient('vitamin-a')
        vit_c = get_nutrient('vitamin-c')
        if vit_a > 0:
            vitamins['Vit A'] = f"{vit_a:.1f} µg"
        if vit_c > 0:
            vitamins['Vit C'] = f"{vit_c:.1f} mg"
        
        # Minerals (if available)
        minerals = {}
        calcium = get_nutrient('calcium')
        iron = get_nutrient('iron')
        sodium = get_nutrient('sodium')
        potassium = get_nutrient('potassium')
        
        if calcium > 0:
            minerals['Calcium'] = f"{calcium:.1f} mg"
        if iron > 0:
            minerals['Iron'] = f"{iron:.1f} mg"
        if sodium > 0:
            minerals['Sodium'] = f"{sodium:.1f} mg"
        if potassium > 0:
            minerals['Potassium'] = f"{potassium:.1f} mg"
        
        return {
            "calories": calories,
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1),
            "fiber": round(fiber, 1),
            "vitamins": vitamins if vitamins else {"Info": "Not available"},
            "minerals": minerals if minerals else {"Info": "Not available"},
        }
    
    except Exception as e:
        print(f"Open Food Facts API error: {e}")
        return None


def get_nutrition_info(food_name: str) -> Optional[Dict]:
    """
    Priority order:
    1. Try local DB (fastest, for common Indian foods)
    2. If not found, try Open Food Facts (FREE, no API key!)
    3. Return None if both fail
    """
    # Try local database first
    local = _lookup_local(food_name)
    if local:
        return local
    
    # Try Open Food Facts API (free!)
    api_data = _fetch_from_openfoodfacts(food_name)
    if api_data:
        return api_data
    
    return None
