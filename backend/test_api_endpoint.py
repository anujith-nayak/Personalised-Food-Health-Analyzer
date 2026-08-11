"""
Verification test for POST /food/analyze-food-label endpoint with PaddleOCR and RapidFuzz pipeline.
"""

import sys
import os
import cv2
import numpy as np

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def make_label_bytes():
    img = np.ones((700, 500, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX

    cv2.rectangle(img, (20, 20), (480, 680), (0, 0, 0), 3)
    cv2.line(img, (20, 70), (480, 70), (0, 0, 0), 4)

    lines = [
        (30, 60,  1.2, "Nutrition Facts", 3),
        (30, 100, 0.65, "Serving Size 30g", 1),
        (30, 140, 0.8, "Amount Per Serving", 2),
        (30, 185, 1.0, "Calories 240 kcal", 3),
        (30, 230, 0.65, "Total Fat 12g", 2),
        (50, 265, 0.6, "Saturated Fat 3.5g", 1),
        (50, 295, 0.6, "Trans Fat 0g", 1),
        (30, 330, 0.65, "Cholesterol 10mg", 2),
        (30, 365, 0.65, "Sodium 340mg", 2),
        (30, 400, 0.65, "Total Carbohydrate 31g", 2),
        (50, 435, 0.6, "Dietary Fiber 3g", 1),
        (50, 465, 0.6, "Total Sugars 5g", 1),
        (30, 500, 0.65, "Protein 4g", 2),
    ]

    for x, y, scale, text, thick in lines:
        cv2.putText(img, text, (x, y), font, scale, (0, 0, 0), thick, cv2.LINE_AA)

    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


def test_end_to_end_api():
    print("=" * 70)
    print("TESTING ENDPOINT VIA FASTAPI TESTCLIENT")
    print("=" * 70)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth.dependencies import get_current_user
    from app.models.user import User

    # Mock user for auth dependency
    mock_user = User(id=1, email="test@example.com", name="Test User", bmi_score=24.5, bmi_category="Normal")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)
    img_bytes = make_label_bytes()

    response = client.post(
        "/food/analyze-food-label",
        files={"file": ("test_label.png", img_bytes, "image/png")}
    )

    print(f"HTTP Status Code: {response.status_code}")
    res_data = response.json()

    print("\n--- API RESPONSE KEYS ---")
    print(list(res_data.keys()))

    print("\n--- ENGINE & CONFIDENCE FIELDS ---")
    print(f"engine_used:        {res_data.get('engine_used')}")
    print(f"is_fallback:        {res_data.get('is_fallback')}")
    print(f"ocr_confidence:     {res_data.get('ocr_confidence')}%")
    print(f"parser_confidence:  {res_data.get('parser_confidence')}%")
    print(f"overall_confidence: {res_data.get('overall_confidence')}%")
    print(f"extraction_status:  {res_data.get('extraction_status')}")

    print("\n--- EXTRACTED NUTRITION FACTS ---")
    print(res_data.get("nutrition_facts"))

    print("\n--- HEALTH SCORING ---")
    print(f"health_score: {res_data.get('health_score')}")
    print(f"risk_level:   {res_data.get('risk_level')}")
    print(f"risk_color:   {res_data.get('risk_color')}")
    print(f"final_rec:    {res_data.get('final_recommendation')}")

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    assert res_data.get("engine_used") == "PaddleOCR", "Engine used should be PaddleOCR"
    assert res_data.get("health_score") is not None, "Health score should be calculated"

    print("\n=" * 70)
    print("ALL API CHECKS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    test_end_to_end_api()
