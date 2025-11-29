# app.py
"""
ScanEat - AI-Powered Food Nutrition Scanner
Upload or capture food images to get instant nutrition analysis,
multi-food plate estimates, daily logging, history, weekly summary,
and smart coaching.
"""

import os
from datetime import datetime, date, timedelta

import streamlit as st
from PIL import Image
from dotenv import load_dotenv
import pandas as pd

from food_recognition import recognize_food_advanced, validate_food_image
from nutrition_api import get_nutrition_info
from recommendations import get_meal_recommendations, get_healthier_alternatives

# Load environment variables from .env (for local dev)
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ScanEat - Food Nutrition Scanner",
    page_icon="🍽️",
    layout="wide"
)

# --- Session state for logs (lives for current browser session) ---
if "log_entries" not in st.session_state:
    # Each entry:
    # {
    #   "date": "YYYY-MM-DD",
    #   "time": "HH:MM",
    #   "foods": ["pizza", "salad"],
    #   "calories": int,
    #   "protein": float,
    #   "carbs": float,
    #   "fat": float,
    #   "fiber": float,
    #   "portion": float,
    #   "goal": "lose/maintain/gain",
    #   "image": PIL.Image (small copy)
    # }
    st.session_state["log_entries"] = []

# --- Helper: get today's entries ---
def get_today_entries():
    today_str = date.today().isoformat()
    return [e for e in st.session_state["log_entries"] if e["date"] == today_str]


# --- Helper: simple smart coach message based on today's log ---
def generate_coach_message(goal: str):
    entries = get_today_entries()
    if not entries:
        return (
            "You haven't logged any meals today yet. "
            "Scan and log your meals to get personalized coaching."
        )

    total_cals = sum(e["calories"] for e in entries)
    total_protein = sum(e["protein"] for e in entries)
    total_carbs = sum(e["carbs"] for e in entries)
    total_fat = sum(e["fat"] for e in entries)
    meals_count = len(entries)

    # Rough target ranges (very simplified)
    if goal == "lose":
        target_min, target_max = 1400, 1900
    elif goal == "gain":
        target_min, target_max = 2200, 2800
    else:
        target_min, target_max = 1800, 2300

    lines = []

    lines.append(f"📊 You logged **{meals_count}** meal(s) today with about **{total_cals} kcal** in total.")
    lines.append(
        f"Approx macros: **Protein** {total_protein:.0f} g, "
        f"**Carbs** {total_carbs:.0f} g, **Fat** {total_fat:.0f} g."
    )

    # Calorie analysis
    if total_cals < target_min:
        if goal == "lose":
            lines.append(
                "You're **below** the typical calorie range for weight loss. "
                "Make sure you're not undereating; add some nutrient-dense foods like dal, paneer, eggs, nuts."
            )
        elif goal == "gain":
            lines.append(
                "You're well **below** the calorie range needed for weight gain. "
                "Add at least one more solid meal or calorie-dense snacks."
            )
        else:
            lines.append(
                "You're **under** a typical maintenance range. "
                "If you feel low on energy, consider adding an extra balanced meal."
            )
    elif total_cals > target_max:
        if goal == "lose":
            lines.append(
                "You're **above** the usual calorie range for weight loss today. "
                "Balance it tomorrow with lighter meals and more activity."
            )
        elif goal == "gain":
            lines.append(
                "You're on the **higher** side of calories, which can support weight gain, "
                "but ensure they come from quality foods, not just junk."
            )
        else:
            lines.append(
                "You're **above** a typical maintenance range. "
                "If days like this are frequent, it may slowly lead to weight gain."
            )
    else:
        if goal == "lose":
            lines.append(
                "Nice! Your total calories are within a reasonable range for weight loss today. "
                "Keep focusing on protein and fiber to stay full."
            )
        elif goal == "gain":
            lines.append(
                "Good! Your total calories are in a decent range for weight gain. "
                "Combine this with strength training to gain mostly muscle."
            )
        else:
            lines.append(
                "You're roughly in a **maintenance** range today. "
                "If your weight stays stable over weeks, this is likely your sweet spot."
            )

    # Protein analysis
    if total_protein < 50:
        lines.append(
            "Protein intake looks on the **lower side**. Try to include more dal, paneer, chana, rajma, eggs or lean meat."
        )
    elif total_protein > 120:
        lines.append(
            "Protein intake is **quite high**, which is okay if you train regularly, but keep hydration up and balance with veggies."
        )
    else:
        lines.append(
            "Protein intake looks **okay** for a typical day. Good job including some protein sources."
        )

    # Carbs & fat brief check
    if total_carbs > total_fat * 4:
        lines.append(
            "Your day leaned more towards **carb-heavy** meals. Try adding some healthy fats (nuts, seeds, ghee in moderation) and protein."
        )
    elif total_fat > total_carbs:
        lines.append(
            "Your day is a bit **fat-heavy**. Reduce deep-fried and creamy foods and replace them with grilled/steamed options."
        )

    # Behaviour advice
    lines.append(
        "💡 Tip: Try to spread your calories across the day (breakfast, lunch, dinner, 1–2 snacks) "
        "instead of having one very heavy meal."
    )

    return "\n\n".join(lines)


# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4ECDC4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .food-name {
        font-size: 2rem;
        color: #2ECC71;
        font-weight: bold;
    }
    .confidence-score {
        font-size: 1.1rem;
        color: #3498DB;
    }
    .nutrition-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .recommendation {
        background-color: #E8F8F5;
        padding: 1rem;
        border-left: 4px solid #1ABC9C;
        margin: 0.5rem 0;
        border-radius: 5px;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<h1 class="main-header">🍽️ ScanEat</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Scan your food. Know your calories. Track your day. Get coached.</p>', unsafe_allow_html=True)

# Warn if no Clarifai key
if not os.getenv("CLARIFAI_API_KEY"):
    st.warning(
        "⚠️ CLARIFAI_API_KEY is not set. Real food detection may not work. "
        "Set it in your .env file or Streamlit secrets."
    )

# --- Sidebar navigation ---
st.sidebar.title("🧭 Navigation")

page = st.sidebar.radio(
    "Go to:",
    ["Scan Food", "Today's Log & History", "Weekly Summary", "Smart Coach"],
)

# Sidebar: health goal
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Your Goal")
goal_label = st.sidebar.selectbox(
    "Health Goal:",
    ["Maintain Weight", "Lose Weight", "Gain Weight"]
)

goal_map = {
    "Maintain Weight": "maintain",
    "Lose Weight": "lose",
    "Gain Weight": "gain"
}
selected_goal = goal_map[goal_label]

# Sidebar: today's summary
today_str = date.today().isoformat()
today_entries = get_today_entries()
today_cals = sum(e["calories"] for e in today_entries) if today_entries else 0

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Today's Summary")

if today_entries:
    st.sidebar.write(f"Meals logged: **{len(today_entries)}**")
    st.sidebar.write(f"Total calories: **{today_cals} kcal**")
    st.sidebar.write("Recent meals:")
    for e in today_entries[-5:][::-1]:
        st.sidebar.write(f"- {e['time']} · {', '.join([f.title() for f in e['foods']])} · {e['calories']} kcal")
else:
    st.sidebar.write("No meals logged yet today.")

# ---------------------- PAGE 1: SCAN FOOD ----------------------
if page == "Scan Food":
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📸 Capture or Upload Food / Image")

        input_method = st.radio(
            "Choose input method:",
            ["📤 Upload Image", "📷 Camera (Live Capture)"],
            horizontal=True
        )

        image = None

        if input_method == "📤 Upload Image":
            uploaded_file = st.file_uploader(
                "Choose an image (food or anything)...",
                type=["jpg", "jpeg", "png"]
            )
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, caption="Your Image", use_column_width=True)
        else:
            camera_photo = st.camera_input("Take a picture")
            if camera_photo is not None:
                image = Image.open(camera_photo)
                st.image(image, caption="Your Image", use_column_width=True)

        st.markdown("""
**Live eating use-case:**  
You're about to eat something → open ScanEat → take a quick photo → hit *Analyze Food* → see calories and decide.
""")

    with col2:
        st.subheader("📊 AI Understanding & Nutrition")

        if image is not None:
            if st.button("🔍 Analyze Food", type="primary", use_container_width=True):
                with st.spinner("Looking at your image..."):
                    try:
                        # 1) Check if this looks like a food photo
                        is_food, validation_confidence = validate_food_image(image)

                        if not is_food or validation_confidence < 0.4:
                            st.warning(
                                "📷 This looks like a **generic image or unclear food**. "
                                "I'll still try to guess what it is."
                            )
                        else:
                            st.success(
                                f"✅ This looks like a **food image** "
                                f"(model confidence ~{validation_confidence*100:.1f}%)."
                            )

                        # 2) Recognize what the image looks like
                        detection = recognize_food_advanced(image)
                        food_name = detection["name"]
                        confidence = detection["confidence"]
                        alternatives = detection.get("alternatives", [])

                        if food_name == "unknown" or confidence < 0.3:
                            st.error(
                                "🤔 I couldn't confidently recognize a specific food item in this image.\n"
                                "It might not be food, or the photo is too unclear.\n\n"
                                "Try a clearer, closer top-view photo of the food on your plate."
                            )
                        else:
                            st.markdown(
                                f'<p class="food-name">🖼️ I see: {food_name.title()}</p>',
                                unsafe_allow_html=True
                            )
                            st.markdown(
                                f'<p class="confidence-score">Model confidence: {confidence*100:.1f}%</p>',
                                unsafe_allow_html=True
                            )

                            if alternatives:
                                st.info(
                                    f"💡 Similar things the AI also sees here: {', '.join(alternatives[:4])}"
                                )

                            # --- Multi-food plate selection ---
                            st.markdown("### 🍽 What's on your plate?")

                            # Candidate list: main food + alternatives
                            candidate_items = [food_name] + [
                                alt for alt in alternatives if isinstance(alt, str)
                            ]

                            selected_items = st.multiselect(
                                "Select all foods you actually see in this image:",
                                options=candidate_items,
                                default=[food_name],
                                help="If the plate has multiple items (e.g., rice + curry + salad), select them all."
                            )

                            # Portion size slider
                            portion = st.slider(
                                "How much of this plate did you (or will you) eat?",
                                min_value=0.25,
                                max_value=2.0,
                                value=1.0,
                                step=0.25,
                                help="0.5 = half plate, 1.0 = full plate, 2.0 = double serving."
                            )

                            combined_nutrition = None

                            if selected_items:
                                combined_nutrition = {
                                    "calories": 0,
                                    "protein": 0.0,
                                    "carbs": 0.0,
                                    "fat": 0.0,
                                    "fiber": 0.0,
                                }
                                missing_items = []

                                for item in selected_items:
                                    n = get_nutrition_info(item)
                                    if not n:
                                        missing_items.append(item)
                                        continue
                                    combined_nutrition["calories"] += n["calories"]
                                    combined_nutrition["protein"] += n["protein"]
                                    combined_nutrition["carbs"] += n["carbs"]
                                    combined_nutrition["fat"] += n["fat"]
                                    combined_nutrition["fiber"] += n.get("fiber", 0.0)

                                # Apply portion factor
                                for k in combined_nutrition:
                                    combined_nutrition[k] *= portion

                                if combined_nutrition["calories"] > 0:
                                    st.markdown("#### 🧮 Estimated plate totals (based on selected items & portion)")
                                    st.markdown('<div class="nutrition-box">', unsafe_allow_html=True)

                                    macros = st.columns(4)
                                    macros[0].metric("🔥 Calories", f"{combined_nutrition['calories']:.0f} kcal")
                                    macros[1].metric("💪 Protein", f"{combined_nutrition['protein']:.1f} g")
                                    macros[2].metric("🍞 Carbs", f"{combined_nutrition['carbs']:.1f} g")
                                    macros[3].metric("🥑 Fat", f"{combined_nutrition['fat']:.1f} g")

                                    st.markdown(f"**Fiber:** {combined_nutrition['fiber']:.1f} g")

                                    st.markdown("</div>", unsafe_allow_html=True)

                                    if missing_items:
                                        st.warning(
                                            "No nutrition data found for: "
                                            + ", ".join(missing_items)
                                            + ". You can extend the database later."
                                        )
                                else:
                                    st.info(
                                        "I couldn't find nutrition data for the selected items. "
                                        "Try selecting a simpler item like 'pizza', 'rice', 'roti', etc."
                                    )

                            # --- Main item nutrition + recs ---
                            main_nutrition = get_nutrition_info(food_name)

                            if main_nutrition:
                                st.markdown("### 📋 Nutrition for main item (1 serving)")
                                st.markdown('<div class="nutrition-box">', unsafe_allow_html=True)

                                macros = st.columns(4)
                                macros[0].metric("🔥 Calories", f"{main_nutrition['calories']} kcal")
                                macros[1].metric("💪 Protein", f"{main_nutrition['protein']} g")
                                macros[2].metric("🍞 Carbs", f"{main_nutrition['carbs']} g")
                                macros[3].metric("🥑 Fat", f"{main_nutrition['fat']} g")

                                st.markdown(f"**Fiber:** {main_nutrition.get('fiber', 0)} g")

                                if main_nutrition.get("vitamins"):
                                    st.markdown("**Top Vitamins:**")
                                    vitamin_text = " | ".join(
                                        [f"{k}: {v}" for k, v in list(main_nutrition["vitamins"].items())[:3]]
                                    )
                                    st.text(vitamin_text)

                                if main_nutrition.get("minerals"):
                                    st.markdown("**Top Minerals:**")
                                    mineral_text = " | ".join(
                                        [f"{k}: {v}" for k, v in list(main_nutrition["minerals"].items())[:3]]
                                    )
                                    st.text(mineral_text)

                                st.markdown("</div>", unsafe_allow_html=True)

                                # Recommendations for main item
                                st.markdown("### 💡 Personalized Recommendations (main item)")
                                recs = get_meal_recommendations(food_name, main_nutrition, selected_goal)
                                for rec in recs:
                                    st.markdown(
                                        f'<div class="recommendation">{rec}</div>',
                                        unsafe_allow_html=True
                                    )

                                # Alternatives for main item
                                st.markdown("### 🥗 Healthier Alternatives (main item)")
                                alt_list = get_healthier_alternatives(food_name)
                                for alt in alt_list:
                                    st.markdown(f"- {alt}")

                                # Weight impact (use combined if available, else main item calories)
                                st.markdown("### ⚖️ Weight Impact")
                                if combined_nutrition and combined_nutrition["calories"] > 0:
                                    used_cals = combined_nutrition["calories"]
                                    used_protein = combined_nutrition["protein"]
                                    used_carbs = combined_nutrition["carbs"]
                                    used_fat = combined_nutrition["fat"]
                                    used_fiber = combined_nutrition["fiber"]
                                else:
                                    used_cals = main_nutrition["calories"] * portion
                                    used_protein = main_nutrition["protein"] * portion
                                    used_carbs = main_nutrition["carbs"] * portion
                                    used_fat = main_nutrition["fat"] * portion
                                    used_fiber = main_nutrition.get("fiber", 0.0) * portion

                                if selected_goal == "lose":
                                    info = (
                                        f"This plate (with portion factor {portion}x) is about **{used_cals:.0f} kcal**. "
                                        "For weight loss, stay in a daily calorie deficit and "
                                        "balance this with lighter meals and activity."
                                    )
                                elif selected_goal == "gain":
                                    info = (
                                        f"This plate (with portion factor {portion}x) is about **{used_cals:.0f} kcal**. "
                                        "For healthy weight gain, combine it with enough protein and strength training."
                                    )
                                else:
                                    info = (
                                        f"This plate (with portion factor {portion}x) is about **{used_cals:.0f} kcal** "
                                        "and can fit into a balanced diet if it matches your total daily calorie needs."
                                    )
                                st.info(info)

                                # --- Add to daily log ---
                                if st.button("➕ Add this meal to today's log"):
                                    now = datetime.now()
                                    entry = {
                                        "date": today_str,
                                        "time": now.strftime("%H:%M"),
                                        "foods": selected_items if selected_items else [food_name],
                                        "calories": int(round(used_cals)),
                                        "protein": float(round(used_protein, 1)),
                                        "carbs": float(round(used_carbs, 1)),
                                        "fat": float(round(used_fat, 1)),
                                        "fiber": float(round(used_fiber, 1)),
                                        "portion": float(portion),
                                        "goal": selected_goal,
                                        "image": image.copy(),
                                    }
                                    st.session_state["log_entries"].append(entry)
                                    st.success("✅ Added to today's log!")
                            else:
                                st.warning(
                                    "I recognized this as a food item but don't have nutrition data for it yet.\n"
                                    "You can extend the local nutrition database or connect more APIs later."
                                )

                    except Exception as e:
                        st.error(f"❌ Error processing image: {e}")

        else:
            st.info("👆 Please upload or capture an image to begin analysis.")

# ---------------------- PAGE 2: TODAY'S LOG & HISTORY ----------------------
elif page == "Today's Log & History":
    st.subheader("📅 Today's Log")

    today_entries = get_today_entries()
    if today_entries:
        total_cals = sum(e["calories"] for e in today_entries)
        total_protein = sum(e["protein"] for e in today_entries)
        total_carbs = sum(e["carbs"] for e in today_entries)
        total_fat = sum(e["fat"] for e in today_entries)

        st.write(f"**Total meals today:** {len(today_entries)}")
        st.write(f"**Total calories:** {total_cals} kcal")
        st.write(
            f"**Total protein:** {total_protein:.1f} g · "
            f"**carbs:** {total_carbs:.1f} g · "
            f"**fat:** {total_fat:.1f} g"
        )

        st.markdown("### 🧾 Detailed meals")
        for e in today_entries[::-1]:
            with st.expander(f"{e['time']} · {', '.join([f.title() for f in e['foods']])} · {e['calories']} kcal"):
                cols = st.columns([1, 2])
                with cols[0]:
                    if e.get("image") is not None:
                        st.image(e["image"], caption="Meal image", use_column_width=True)
                with cols[1]:
                    st.write(f"**Foods:** {', '.join([f.title() for f in e['foods']])}")
                    st.write(f"**Calories:** {e['calories']} kcal")
                    st.write(
                        f"**Protein:** {e['protein']} g · "
                        f"**Carbs:** {e['carbs']} g · "
                        f"**Fat:** {e['fat']} g · "
                        f"**Fiber:** {e['fiber']} g"
                    )
                    st.write(f"**Portion factor:** {e['portion']}x")
                    st.write(f"**Goal at time of log:** {e['goal']}")

    else:
        st.info("No meals logged today yet. Go to **Scan Food** and add one.")

    st.markdown("---")
    st.subheader("📚 Full Session History (All Days in this Session)")

    if st.session_state["log_entries"]:
        # For table + export, drop the image field
        table_data = []
        for e in st.session_state["log_entries"]:
            row = {
                "date": e["date"],
                "time": e["time"],
                "foods": ", ".join(e["foods"]),
                "calories": e["calories"],
                "protein": e["protein"],
                "carbs": e["carbs"],
                "fat": e["fat"],
                "fiber": e["fiber"],
                "portion": e["portion"],
                "goal": e["goal"],
            }
            table_data.append(row)

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

        # Export as CSV
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download full log as CSV",
            data=csv_bytes,
            file_name="scaneat_log.csv",
            mime="text/csv",
        )
    else:
        st.info("No history in this session yet.")

# ---------------------- PAGE 3: WEEKLY SUMMARY ----------------------
elif page == "Weekly Summary":
    st.subheader("📈 Weekly Summary (based on current session logs)")

    logs = st.session_state["log_entries"]
    if not logs:
        st.info(
            "No logs yet. Start scanning and logging meals, "
            "then come back here to see your weekly summary."
        )
    else:
        # Last 7 days including today
        today_dt = date.today()
        start_dt = today_dt - timedelta(days=6)

        filtered = [
            e for e in logs
            if start_dt <= datetime.fromisoformat(e["date"]).date() <= today_dt
        ]

        if not filtered:
            st.info("No entries in the last 7 days.")
        else:
            # Aggregate calories per day
            day_map = {}
            for e in filtered:
                d = e["date"]
                day_map.setdefault(d, 0)
                day_map[d] += e["calories"]

            # Ensure all 7 days appear
            dates_list = [(start_dt + timedelta(days=i)).isoformat() for i in range(7)]
            cals_list = [day_map.get(d, 0) for d in dates_list]

            df = pd.DataFrame({
                "date": dates_list,
                "calories": cals_list,
            })

            st.write("**Calories per day (last 7 days):**")
            st.bar_chart(df.set_index("date"))

            total_week_cals = sum(cals_list)
            avg_daily_cals = total_week_cals / 7.0

            st.write(f"**Total calories in last 7 days:** {total_week_cals:.0f} kcal")
            st.write(f"**Average calories per day:** {avg_daily_cals:.0f} kcal")

            # Top foods this week
            food_counts = {}
            for e in filtered:
                for f in e["foods"]:
                    food_counts[f] = food_counts.get(f, 0) + 1

            if food_counts:
                top_foods = sorted(food_counts.items(), key=lambda x: x[1], reverse=True)
                st.markdown("### 🍛 Most frequently eaten foods this week")
                for name, count in top_foods[:5]:
                    st.write(f"- {name.title()} · {count} time(s)")

# ---------------------- PAGE 4: SMART COACH ----------------------
elif page == "Smart Coach":
    st.subheader("🧠 Smart Coach")

    message = generate_coach_message(selected_goal)
    st.markdown(message)
    st.markdown("---")
    st.info(
        "This coach is a simple heuristic based on your logged calories and macros. "
        "It's not a medical or dietician-grade plan, but a helpful guide."
    )

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #95a5a6; font-size: 0.9rem;'>
    Made with ❤️ by Sunil · ScanEat v4.0
</div>
""", unsafe_allow_html=True)
