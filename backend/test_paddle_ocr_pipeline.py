"""
Comprehensive verification test for PaddleOCR + RapidFuzz Nutrition Parser architecture.
Tests image quality check, ROI table cropping, PaddleOCR extraction, RapidFuzz nutrient parsing,
unit normalization, and confidence calculation.
"""

import sys
import os
import cv2
import numpy as np

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_realistic_nutrition_label() -> str:
    """Generates a realistic synthetic nutrition facts table image."""
    img = np.ones((700, 500, 3), dtype=np.uint8) * 255  # white background
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Draw border lines to simulate a real label panel
    cv2.rectangle(img, (20, 20), (480, 680), (0, 0, 0), 3)
    cv2.line(img, (20, 70), (480, 70), (0, 0, 0), 4)
    cv2.line(img, (20, 115), (480, 115), (0, 0, 0), 2)
    cv2.line(img, (20, 150), (480, 150), (0, 0, 0), 4)

    lines = [
        (30, 60,  1.2, "Nutrition Facts", 3),
        (30, 100, 0.65, "Serving Size 1 container (30g)", 1),
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
        (30, 545, 0.6, "Potassium 220mg", 1),
        (30, 575, 0.6, "Calcium 80mg", 1),
        (30, 605, 0.6, "Iron 2.5mg", 1),
    ]

    for x, y, scale, text, thick in lines:
        cv2.putText(img, text, (x, y), font, scale, (0, 0, 0), thick, cv2.LINE_AA)

    output_path = os.path.join(os.path.dirname(__file__), "synthetic_test_label.png")
    cv2.imwrite(output_path, img)
    return output_path


def run_pipeline_test():
    print("=" * 70)
    print("STARTING PADDLEOCR + RAPIDFUZZ PIPELINE VERIFICATION TEST")
    print("=" * 70)

    label_path = create_realistic_nutrition_label()
    with open(label_path, "rb") as f:
        image_bytes = f.read()

    from app.services.ocr_service import extract_ocr_result
    from app.services.ocr.nutrient_parser import NutrientParser
    from app.services.ingredient_extractor import parse_food_label

    print("\n1. Running OCR Service (cropper + PaddleOCR)...")
    ocr_res, crop_meta = extract_ocr_result(image_bytes)

    print(f"\n--- OCR ENGINE VERIFICATION ---")
    print(f"Active OCR Engine: {ocr_res.engine_name}")
    print(f"Is Fallback Used:  {ocr_res.is_fallback}")
    print(f"OCR Confidence:    {ocr_res.ocr_confidence}%")
    print(f"Processing Time:   {ocr_res.processing_time_ms} ms")
    print(f"Cropper Metadata:  {crop_meta}")

    print("\n--- RAW OCR TEXT LINES ---")
    print(ocr_res.raw_text)

    print("\n2. Running RapidFuzz Nutrient Parser...")
    parser = NutrientParser()
    parse_result = parser.parse(ocr_res)

    print("\n--- PARSER RESULTS ---")
    print(f"Parser Confidence:  {parse_result['parser_confidence']}%")
    print(f"Overall Confidence: {parse_result['overall_confidence']}%")
    print(f"Extraction Status:  {parse_result['extraction_status']}")
    print(f"Is Partial:         {parse_result['is_partial']}")
    print(f"Missing Nutrients:  {parse_result['missing_nutrients']}")
    print(f"Matched Nutrients:  {parse_result['matched_nutrient_names']}")

    print("\n--- EXTRACTED NUTRITION DICTIONARY ---")
    extracted_nutrients = parse_result["nutrition"]
    for k, v in extracted_nutrients.items():
        print(f"  {k:20}: {v}")

    # Minimum targets verification
    required_keys = ["calories", "protein", "total_fat", "saturated_fat", "carbohydrates", "sugar", "sodium"]
    missing_required = [k for k in required_keys if extracted_nutrients.get(k) is None]

    print("\n--- MINIMUM REQUIRED NUTRIENTS VERIFICATION ---")
    if not missing_required:
        print("SUCCESS: All 7 required minimum target nutrients extracted cleanly!")
    else:
        print(f"WARNING: Missed required nutrients: {missing_required}")

    # Cleanup
    if os.path.exists(label_path):
        os.remove(label_path)

    print("\n=" * 70)
    print("PIPELINE VERIFICATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline_test()
