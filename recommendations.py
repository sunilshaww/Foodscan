# recommendations.py
from typing import Dict, List

HEALTHIER_ALTERNATIVES_MAP = {
    "pizza": [
        "Thin-crust veggie pizza with less cheese.",
        "Whole-wheat base pizza with extra veggies.",
        "Grilled paneer wrap instead of heavy cheese pizza.",
    ],
    "burger": [
        "Grilled paneer or chicken burger without mayo.",
        "Whole-wheat bun with extra salad and less cheese.",
        "Veggie burger with baked patty instead of fried.",
    ],
    "biryani": [
        "Veg pulao with less oil and more vegetables.",
        "Grilled chicken + rice instead of oily biryani.",
        "Brown rice biryani with less ghee.",
    ],
    "paneer butter masala": [
        "Paneer tikka (grilled) instead of heavy gravy.",
        "Paneer curry with less cream and oil.",
        "Dal + sabzi + roti instead of rich gravy.",
    ],
    "idli": [
        "Plain idli with sambar and less chutney.",
        "Rava idli with less oil.",
        "Steamed dhokla as another light option.",
    ],
    "dosa": [
        "Plain dosa with less oil instead of masala dosa.",
        "Ragi dosa for more fiber.",
        "Utthapam loaded with veggies.",
    ],
    "salad": [
        "Add protein like boiled egg / paneer / chana.",
        "Use olive oil + lemon instead of creamy dressing.",
        "Mix fruits + veggies for micronutrients.",
    ],
    "rice": [
        "Switch to brown rice sometimes for more fiber.",
        "Mix rice with dal and veggies for better balance.",
        "Control portion size and add salad on the side.",
    ],
    "roti": [
        "Use multi-grain atta instead of maida.",
        "Use ghee in small quantity if needed.",
        "Pair 2 rotis with sabzi + dal instead of many rotis alone.",
    ],
}


def get_meal_recommendations(food_name: str, nutrition: Dict, goal: str) -> List[str]:
    recs: List[str] = []

    calories = nutrition.get("calories", 0)
    protein = nutrition.get("protein", 0.0)
    carbs = nutrition.get("carbs", 0.0)
    fat = nutrition.get("fat", 0.0)
    fiber = nutrition.get("fiber", 0.0)

    # Goal-specific guidance
    if goal == "lose":
        if calories > 600:
            recs.append(
                f"This looks like a high-calorie meal (~{calories} kcal). "
                "For weight loss, reduce portion size, share it, or balance with very light meals."
            )
        else:
            recs.append(
                f"At around {calories} kcal, this can fit a weight loss plan "
                "if your daily calories remain in deficit."
            )
        if fat > 20:
            recs.append("Fat is on the higher side. Avoid adding extra ghee, butter, or fried sides.")
        if fiber < 3:
            recs.append("Fiber is low. Add salad, fruits, or vegetables with this meal to stay full longer.")
    elif goal == "gain":
        if calories < 400:
            recs.append(
                f"This meal has only ~{calories} kcal. For healthy weight gain, "
                "consider adding an extra roti, rice, or a protein-rich side."
            )
        else:
            recs.append(
                f"With ~{calories} kcal, this supports a calorie surplus if combined with your other meals."
            )
        if protein < 15:
            recs.append(
                "Protein is on the lower side. For muscle gain, add paneer, lentils, eggs, or whey."
            )
    else:  # maintain
        recs.append(
            f"With ~{calories} kcal, this can fit into a balanced diet "
            "if your overall daily intake is around your maintenance level."
        )
        if fat > 25:
            recs.append("Fat is slightly high. Reduce cream-based gravies or deep-fried items.")
        if carbs > 50:
            recs.append("Carbs are high. Balance with more protein and fiber in other meals.")

    # General tips
    if protein < 10:
        recs.append(
            "Add a protein-rich side (dal, paneer, chana, rajma, eggs) to make this meal more filling and muscle-friendly."
        )
    if fiber < 2:
        recs.append(
            "Very low fiber. Add salad, fruits, or whole grains for better digestion and satiety."
        )

    food_key = food_name.lower()
    # Time-of-day style hints
    if "biryani" in food_key or "butter" in food_key or "fried" in food_key:
        recs.append(
            "Try to avoid very heavy, oily foods late at night. If you eat this for dinner, keep the portion small."
        )
    if "salad" in food_key or "idli" in food_key or "dosa" in food_key:
        recs.append(
            "This can be a good choice for breakfast or dinner when paired with some protein."
        )

    return recs


def get_healthier_alternatives(food_name: str) -> List[str]:
    key = food_name.strip().lower()
    if key in HEALTHIER_ALTERNATIVES_MAP:
        return HEALTHIER_ALTERNATIVES_MAP[key]
    for k, v in HEALTHIER_ALTERNATIVES_MAP.items():
        if key in k or k in key:
            return v
    return [
        "Reduce portion size slightly and add more salad or vegetables.",
        "Avoid sugary drinks with this meal; choose water, buttermilk, or lemon water.",
        "Replace deep-fried sides with grilled, steamed, or roasted options.",
    ]
