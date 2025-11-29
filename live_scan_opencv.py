# live_scan_opencv.py
"""
ScanEat Live - desktop script using OpenCV.
Shows live webcam feed with detected food name and approximate calories.
"""

import time

import cv2
from PIL import Image
from dotenv import load_dotenv

from food_recognition import recognize_food_advanced, validate_food_image
from nutrition_api import get_nutrition_info

load_dotenv()


def main():
    cap = cv2.VideoCapture(0)  # default webcam

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    last_prediction_time = 0.0
    prediction_interval = 2.0  # seconds between predictions

    current_label = "Point your plate to the camera..."
    current_conf = 0.0
    current_cals = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        text = current_label
        if current_conf > 0:
            text = f"{current_label} ({current_conf*100:.1f}%)"
        if current_cals is not None:
            text = f"{text} · ~{current_cals} kcal"

        cv2.putText(
            frame,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        cv2.imshow("ScanEat Live - Press Q to quit", frame)

        now = time.time()
        if now - last_prediction_time > prediction_interval:
            last_prediction_time = now

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)

            is_food, conf = validate_food_image(pil_img)
            if not is_food or conf < 0.5:
                current_label = "Not clear / not recognized as food"
                current_conf = 0.0
                current_cals = None
            else:
                result = recognize_food_advanced(pil_img)
                name = result.get("name", "unknown")
                c = result.get("confidence", 0.0)
                if name == "unknown" or c < 0.5:
                    current_label = "Could not detect specific food"
                    current_conf = 0.0
                    current_cals = None
                else:
                    current_label = name
                    current_conf = c
                    n = get_nutrition_info(name)
                    if n:
                        current_cals = n["calories"]
                    else:
                        current_cals = None

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
