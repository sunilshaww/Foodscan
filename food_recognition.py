# food_recognition.py
import os
import io
import base64
from typing import Tuple, Dict, List, Optional

import requests
from PIL import Image
from dotenv import load_dotenv

# Load env (for local runs; on Streamlit Cloud, secrets are used)
load_dotenv()

CLARIFAI_API_KEY = os.getenv("CLARIFAI_API_KEY")
CLARIFAI_FOOD_MODEL_URL = "https://api.clarifai.com/v2/models/food-item-recognition/outputs"

# Confidence threshold to consider a prediction valid
FOOD_CONFIDENCE_THRESHOLD = 0.5


def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64-encoded JPEG string."""
    buffer = io.BytesIO()
    image = image.convert("RGB")
    image.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _clarifai_predict(image: Image.Image) -> Optional[List[Dict]]:
    """
    Call Clarifai Food model and return a list of concepts.
    Each concept: {"name": "pizza", "value": 0.97}

    Returns None if API key missing or API fails.
    """
    if not CLARIFAI_API_KEY:
        return None

    try:
        img_b64 = _image_to_base64(image)
        headers = {
            "Authorization": f"Key {CLARIFAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [
                {
                    "data": {
                        "image": {
                            "base64": img_b64
                        }
                    }
                }
            ]
        }

        resp = requests.post(CLARIFAI_FOOD_MODEL_URL, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        concepts = (
            data.get("outputs", [{}])[0]
            .get("data", {})
            .get("concepts", [])
        )
        return concepts
    except Exception:
        return None


def validate_food_image(image: Image.Image) -> Tuple[bool, float]:
    """
    Returns (is_food, confidence).

    - If Clarifai is available:
        - Use the top concept confidence.
        - If confidence >= threshold → treat as food.
        - Else → not food / unclear.
    - If Clarifai is NOT available:
        - Return (False, 0.0) so the app can warn the developer.
    """
    concepts = _clarifai_predict(image)
    if not concepts:
        return False, 0.0

    top = concepts[0]
    confidence = float(top.get("value", 0.0))
    is_food = confidence >= FOOD_CONFIDENCE_THRESHOLD

    return is_food, confidence


def recognize_food_advanced(image: Image.Image) -> Dict:
    """
    Detect food name and confidence.

    Returns:
      {
        "name": "pizza" or "unknown",
        "confidence": 0.92,
        "alternatives": ["cheese pizza", "margherita", ...]
      }

    If not confident enough or API fails → name="unknown".
    """
    concepts = _clarifai_predict(image)

    if not concepts:
        return {
            "name": "unknown",
            "confidence": 0.0,
            "alternatives": [],
        }

    # Sort concepts by confidence
    concepts = sorted(concepts, key=lambda c: c.get("value", 0.0), reverse=True)
    main = concepts[0]
    food_name = main.get("name", "unknown")
    confidence = float(main.get("value", 0.0))

    if confidence < FOOD_CONFIDENCE_THRESHOLD:
        return {
            "name": "unknown",
            "confidence": confidence,
            "alternatives": [],
        }

    alternatives = [
        c.get("name", "")
        for c in concepts[1:6]
        if c.get("name") and float(c.get("value", 0.0)) >= 0.2
    ]

    return {
        "name": food_name,
        "confidence": confidence,
        "alternatives": alternatives,
    }
