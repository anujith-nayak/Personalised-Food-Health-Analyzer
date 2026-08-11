"""
MCH Blood Report Comprehensive Regression Test Suite
===================================================
Tests complete data flow for image-based MCH blood report OCR:
1. Exact parameter count: len(results) == 6
2. Zero metadata leakage (Sabrina, April 8 1993, February 12 2023, 00-991-23, F, Gender, DOB)
3. Exact observed result isolation:
   - Hemoglobin (Hb) = 14.2 g/dL (Ref: 13.5 - 17.5) [Status: Valid]
   - Hematocrit (Hct) = 42.0 % (Ref: 38.3 - 48.6) [Status: Valid]
   - Red Blood Cell Count (RBC) = 5.2 mill/cmm (Ref: 4.5 - 6.0) [Status: Valid]
   - Mean Corpuscular Hemoglobin (MCH) = 27.3 pg (Ref: 27.0 - 33.0) [Status: Valid]
   - Mean Corpuscular Hemoglobin Concentration (MCHC) = 32.5 g/dL (Ref: 31.5 - 35.5) [Status: Valid]
   - Red Cell Distribution Width (RDW) = 12.4 % (Ref: 11.5 - 14.5) [Status: Valid]
4. Zero "00-991" reference range usage.
5. User confirmation & DB persistence.
"""

import os
import sys
import io
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.db import SessionLocal
from app.models.user import User
from app.services.blood_report.report_ocr import extract_structured_blood_report_ocr
from app.services.blood_report.report_parser import BloodReportParser
from app.services.blood_report.report_validator import validate_extracted_results
from app.services.blood_report.report_service import process_report_upload, confirm_report_results, get_user_blood_report


def run_mch_regression_test():
    img_path = os.path.join(
        os.path.dirname(__file__),
        "storage",
        "blood_reports",
        "user_4_20260810_165829_mch-blood-test-reports-example.jpg",
    )

    if not os.path.exists(img_path):
        print(f"[FAIL] Sample MCH report image file not found at: {img_path}")
        sys.exit(1)

    with open(img_path, "rb") as f:
        image_bytes = f.read()

    print("================================================================================")
    print("RUNNING MCH BLOOD REPORT REGRESSION TEST")
    print("================================================================================")

    # Step 1: Run OCR & Parsing
    ocr_res = extract_structured_blood_report_ocr(image_bytes, "mch-report.jpg")
    parser = BloodReportParser()
    extracted = parser.parse_ocr_result(ocr_res)
    validated = validate_extracted_results(extracted)

    print(f"\n1. EXTRACTED PARAMETERS ({len(validated)} TOTAL):")
    print("-" * 80)
    print(f"{'KEY':20s} | {'DISPLAY NAME':40s} | {'VALUE':8s} | {'UNIT':8s} | {'STATUS':10s}")
    print("-" * 80)
    for p in validated:
        print(f"{p['parameter_key']:20s} | {p['display_name']:40s} | {p['value']!s:8s} | {p['unit']:8s} | {p['status']:10s}")

    # Assertion 1: Exactly 6 results extracted
    assert len(validated) == 6, f"Expected exactly 6 extracted parameters, got {len(validated)}"
    print("\n[OK] Assertion passed: Exactly 6 lab parameters extracted.")

    # Convert to dictionary map by parameter_key
    p_map = {item["parameter_key"]: item for item in validated}

    # Assertion 2: Check canonical keys
    expected_keys = {"hemoglobin", "hematocrit", "rbc", "mch", "mchc", "rdw"}
    assert set(p_map.keys()) == expected_keys, f"Expected keys {expected_keys}, got {set(p_map.keys())}"
    print("[OK] Assertion passed: Canonical parameter keys are correct.")

    # Assertion 3: Check observed values
    assert p_map["hemoglobin"]["value"] == 14.2, f"Hemoglobin value expected 14.2, got {p_map['hemoglobin']['value']}"
    assert p_map["hematocrit"]["value"] == 42.0, f"Hematocrit value expected 42.0, got {p_map['hematocrit']['value']}"
    assert p_map["rbc"]["value"] == 5.2, f"RBC value expected 5.2, got {p_map['rbc']['value']}"
    assert p_map["mch"]["value"] == 27.3, f"MCH value expected 27.3, got {p_map['mch']['value']}"
    assert p_map["mchc"]["value"] == 32.5, f"MCHC value expected 32.5, got {p_map['mchc']['value']}"
    assert p_map["rdw"]["value"] == 12.4, f"RDW value expected 12.4, got {p_map['rdw']['value']}"
    print("[OK] Assertion passed: Observed numeric values match ground truth perfectly.")

    # Assertion 4: Check validation status
    for key in expected_keys:
        assert p_map[key]["status"] == "Valid", f"Expected status 'Valid' for {key}, got {p_map[key]['status']}"
    print("[OK] Assertion passed: All 6 valid lab parameters flagged with status 'Valid'.")

    # Assertion 5: Check zero metadata leakage
    forbidden_terms = ["sabrina", "welder", "gender", "april", "february", "00-991", "1993", "2023", "mrn", "patient"]
    for item in validated:
        full_str = f"{item['parameter_key']} {item['display_name']} {item['reference_range']}".lower()
        for term in forbidden_terms:
            assert term not in full_str, f"Metadata leakage detected: '{term}' found in {item}"
    print("[OK] Assertion passed: Zero metadata leakage detected.")

    # Assertion 6: No 00-991 used as reference range
    for item in validated:
        assert "00-991" not in item["reference_range"], f"Invalid reference range '00-991' found in {item}"
    print("[OK] Assertion passed: No '00-991' reference range contamination.")

    # Step 2: Test Database persistence & user confirmation flow
    with SessionLocal() as db:
        user = db.query(User).first()
        if not user:
            user = User(email="test_mch@example.com", name="MCH Test User")
            db.add(user)
            db.commit()
            db.refresh(user)

        # Upload image report via process_report_upload
        upload_res = process_report_upload(db, user.id, image_bytes, "mch_image_report.jpg")
        report_id = upload_res["report_id"]
        assert len(upload_res["results"]) == 6, f"Upload response expected 6 results, got {len(upload_res['results'])}"

        # Confirm results
        confirmed_res = confirm_report_results(db, user.id, report_id, upload_res["results"])
        assert confirmed_res["confirmed_count"] == 6, f"Expected 6 confirmed parameters, got {confirmed_res['confirmed_count']}"

        # Fetch active report
        active_report = get_user_blood_report(db, user.id)
        assert active_report is not None
        assert active_report["status"] == "confirmed"
        assert len(active_report["results"]) == 6

        print("\n[OK] Database upload and user confirmation workflow verified successfully.")

    print("================================================================================")
    print("ALL MCH REGRESSION TESTS PASSED CLEANLY!")
    print("================================================================================")


if __name__ == "__main__":
    run_mch_regression_test()
