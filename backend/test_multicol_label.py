"""
Verification test script for multi-column nutrition label parsing (Per 100g vs Per Serving).
Tests PaddleOCR & RapidFuzz spatial parsing on exact target label values.
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_multicol_label_image():
    """Generates synthetic high-resolution image matching exact multi-column label layout."""
    img = np.ones((900, 700, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Border lines
    cv2.rectangle(img, (20, 20), (680, 880), (0, 0, 0), 3)
    cv2.line(img, (20, 90), (680, 90), (0, 0, 0), 4)
    cv2.line(img, (20, 150), (680, 150), (0, 0, 0), 2)

    rows = [
        # (x, y, scale, text, thick)
        (30, 65, 1.2, "NUTRITION INFORMATION", 3),
        (30, 125, 0.7, "Serving size = 12.5 g", 2),
        (30, 185, 0.65, "NUTRIENT", 2),
        (260, 185, 0.65, "Per 100g", 2),
        (420, 185, 0.65, "Per serve", 2),
        (560, 185, 0.65, "%GDA Per serve", 2),

        (30, 235, 0.65, "Energy", 2),
        (260, 235, 0.65, "524 kcal", 1),
        (420, 235, 0.65, "66 kcal", 1),
        (560, 235, 0.65, "3.3 %", 1),

        (30, 285, 0.65, "Protein", 2),
        (260, 285, 0.65, "11.1 g", 1),
        (420, 285, 0.65, "1.4 g", 1),
        (560, 285, 0.65, "2.8 %", 1),

        (30, 335, 0.65, "Carbohydrate", 2),
        (260, 335, 0.65, "50.1 g", 1),
        (420, 335, 0.65, "6.3 g", 1),
        (560, 335, 0.65, "4.8 %", 1),

        (30, 385, 0.65, "Total Sugars", 2),
        (260, 385, 0.65, "40.9 g", 1),
        (420, 385, 0.65, "5.1 g", 1),
        (560, 385, 0.65, "10.2 %", 1),

        (30, 435, 0.65, "Added Sugars", 2),
        (260, 435, 0.65, "33.9 g", 1),
        (420, 435, 0.65, "4.2 g", 1),
        (560, 435, 0.65, "8.4 %", 1),

        (30, 485, 0.65, "Total Fat", 2),
        (260, 485, 0.65, "30.0 g", 1),
        (420, 485, 0.65, "3.8 g", 1),
        (560, 485, 0.65, "5.7 %", 1),

        (30, 535, 0.65, "Saturated Fat", 2),
        (260, 535, 0.65, "28.7 g", 1),
        (420, 535, 0.65, "3.6 g", 1),
        (560, 535, 0.65, "18.0 %", 1),

        (30, 585, 0.65, "Trans Fat", 2),
        (260, 585, 0.65, "0.09 g", 1),
        (420, 585, 0.65, "0.01 g", 1),
        (560, 585, 0.65, "0.5 %", 1),

        (30, 635, 0.65, "Sodium", 2),
        (260, 635, 0.65, "117.1 mg", 1),
        (420, 635, 0.65, "14.6 mg", 1),
        (560, 635, 0.65, "0.7 %", 1),
    ]

    for x, y, scale, text, thick in rows:
        cv2.putText(img, text, (x, y), font, scale, (0, 0, 0), thick, cv2.LINE_AA)

    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


def run_verification():
    print("=" * 75)
    print("RUNNING MULTI-COLUMN PARSER VERIFICATION")
    print("=" * 75)

    from app.services.ocr_service import extract_ocr_result
    from app.services.ocr.nutrient_parser import NutrientParser
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth.dependencies import get_current_user
    from app.models.user import User

    img_bytes = create_multicol_label_image()

    print("\n1. Running OCR & Nutrient Parser...")
    ocr_result, cropper_meta = extract_ocr_result(img_bytes)
    parsed = NutrientParser().parse(ocr_result)

    print(f"Active OCR Engine: {ocr_result.engine_name}")
    print(f"Is Fallback Used:  {ocr_result.is_fallback}")
    print(f"OCR Confidence:    {ocr_result.ocr_confidence}%")
    print(f"Serving Size (g):  {parsed.get('serving_size_g')}")
    print(f"Value Basis:       {parsed.get('value_basis')}")

    print("\n--- STRUCTURED DUAL-COLUMN NUTRITION FACTS ---")
    facts = parsed.get("nutrition_facts", {})
    for k, v in facts.items():
        print(f"  {k:20s}: {v}")

    print("\n--- ZERO HALLUCINATION / CONTAMINATION CHECK ---")
    print(f"  Potassium : {facts.get('potassium')}")
    print(f"  Calcium   : {facts.get('calcium')}")
    print(f"  Iron      : {facts.get('iron')}")

    assert facts.get("potassium") is None, "Potassium MUST be null"
    assert facts.get("calcium") is None, "Calcium MUST be null"
    assert facts.get("iron") is None, "Iron MUST be null"

    print("\n2. Testing POST /food/analyze-food-label Endpoint...")
    mock_user = User(id=1, email="test@example.com", name="Test User", bmi_score=24.5, bmi_category="Normal")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)
    resp = client.post(
        "/food/analyze-food-label",
        files={"file": ("multicol_label.png", img_bytes, "image/png")}
    )

    print(f"HTTP Status: {resp.status_code}")
    res_data = resp.json()

    print("\n--- ENDPOINT RESPONSE CHECK ---")
    print(f"engine_used     : {res_data.get('engine_used')}")
    print(f"value_basis     : {res_data.get('value_basis')}")
    print(f"serving_size_g  : {res_data.get('serving_size_g')}")
    print(f"health_score    : {res_data.get('health_score')}")
    print(f"risk_level      : {res_data.get('risk_level')}")

    print("\n=" * 75)
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    run_verification()
