"""
OCR smoke test — creates a synthetic food label image and runs the full pipeline.
Run: python test_ocr.py
"""
import numpy as np
import cv2
import sys

# ── Create a synthetic food label image ──────────────────────────────────────
def make_test_label():
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255  # white background
    font = cv2.FONT_HERSHEY_SIMPLEX

    lines = [
        (30, 60,  1.4, "LAYS CLASSIC CHIPS", 2),
        (30, 110, 0.8, "Ingredients: Potato, Vegetable Oil,", 1),
        (30, 145, 0.8, "Salt, Sugar, Maida, Glucose Syrup,", 1),
        (30, 180, 0.8, "Milk Solids, Artificial Flavour", 1),
        (30, 230, 0.9, "Nutrition Facts (per 30g serving)", 1),
        (30, 270, 0.8, "Calories: 480 kcal", 1),
        (30, 305, 0.8, "Total Fat: 28g", 1),
        (30, 340, 0.8, "Saturated Fat: 8g", 1),
        (30, 375, 0.8, "Sodium: 320mg", 1),
        (30, 410, 0.8, "Total Carbohydrates: 52g", 1),
        (30, 445, 0.8, "Sugar: 2g", 1),
        (30, 480, 0.8, "Protein: 5g", 1),
        (30, 515, 0.8, "Serving Size: 30g", 1),
    ]
    for x, y, scale, text, thick in lines:
        cv2.putText(img, text, (x, y), font, scale, (0, 0, 0), thick, cv2.LINE_AA)

    path = "test_label.png"
    cv2.imwrite(path, img)
    return path

# ── Run OCR pipeline ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Creating synthetic food label...")
    img_path = make_test_label()

    from app.services.ocr_service import extract_text_from_image
    from app.services.ingredient_extractor import parse_food_label

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    print("\n--- Running OCR ---")
    text = extract_text_from_image(img_bytes)
    print("Raw OCR text:\n", text[:500])

    print("\n--- Parsing Label ---")
    result = parse_food_label(text)
    print("Product:    ", result["product_name"])
    print("Ingredients:", result["ingredients"])
    print("Nutrition:  ", result["nutrition"])

    # Cleanup
    import os
    os.remove(img_path)
    print("\nOCR test PASSED!")
