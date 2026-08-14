"""
Automated Test Suite for Evidence-Based Nutrition Knowledge Base Module
"""

import os
import sys

# Ensure backend directory is on sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.knowledge_base.database import (
    init_kb_db,
    KBSessionLocal,
    BloodParameter,
    NutritionAction,
    FoodExample,
    Reference,
)
from app.services.knowledge_base.seed_database import seed_knowledge_base
from app.services.knowledge_base.blood_parameter_interpreter import (
    interpret_blood_parameters,
)
from app.services.knowledge_base.knowledge_service import (
    get_conditions_from_report,
    get_nutrition_actions,
    get_food_recommendations,
)
from app.services.knowledge_base.recommendation_engine import (
    KnowledgeBaseRecommendationEngine,
)


def run_tests():
    print("==========================================================")
    print("RUNNING KNOWLEDGE BASE AUTOMATED TEST SUITE")
    print("==========================================================")

    # Step 1: Initialize DB & Seed
    init_kb_db()
    seed_knowledge_base()

    db = KBSessionLocal()
    try:
        # Test Table 1: Blood Parameters count
        param_count = db.query(BloodParameter).count()
        print(f"[TEST 1] Blood Parameters in DB: {param_count}")
        assert param_count >= 20, f"Expected at least 20 parameters, found {param_count}"

        # Test Table 5: Scientific References count
        ref_count = db.query(Reference).count()
        print(f"[TEST 2] Scientific Evidence Sources in DB: {ref_count}")
        assert ref_count >= 5, f"Expected at least 5 evidence sources, found {ref_count}"

        # Step 2: Interpreter Test
        sample_input = {
            "Hemoglobin": 18.1,
            "HbA1c": 7.4,
            "LDL": 180.0,
            "Creatinine": 1.8,
        }
        interpreted = interpret_blood_parameters(sample_input, db=db)
        print(f"[TEST 3] Interpreted output for sample input:")
        for item in interpreted:
            print(f"  - {item['parameter']}: {item['value']} {item['unit']} -> Condition: {item['condition']}")

        expected_params = {"Hemoglobin", "HbA1c", "LDL", "Creatinine"}
        found_params = {i["parameter"] for i in interpreted}
        assert expected_params.issubset(found_params), f"Missing parameters in output: {expected_params - found_params}"
        for i in interpreted:
            assert i["condition"] == "High", f"Expected High for {i['parameter']}, got {i['condition']}"

        # Step 3: Knowledge Service Test
        actions = get_nutrition_actions(interpreted, db=db)
        print(f"[TEST 4] Nutrition Actions retrieved: {len(actions)}")
        for act in actions:
            print(f"  - {act['parameter']} ({act['condition']}) -> Action: {act['action']} {act['nutrient']} | Source: {act['evidence_source']}")

        assert len(actions) > 0, "No nutrition actions returned"

        food_recs = get_food_recommendations(actions, db=db)
        print(f"[TEST 5] Food Recommendations retrieved: {len(food_recs)}")
        for f in food_recs[:5]:
            print(f"  - {f['nutrient']} [{f['action']}]: {f['food_name']} ({f['category']})")

        assert len(food_recs) > 0, "No food recommendations returned"

        # Step 4: Recommendation Engine Test
        engine = KnowledgeBaseRecommendationEngine(db=db)
        output = engine.generate_recommendations(blood_report_values=sample_input)

        print("\n[TEST 6] Engine Merged Output:")
        print(f"  Avoid: {output['avoid']}")
        print(f"  Limit: {output['limit']}")
        print(f"  Increase: {output['increase']}")
        print(f"  Reasons: {output['reasons']}")
        print(f"  Biomarker Analysis Count: {len(output['biomarker_analysis'])}")

        assert "Iron" in output["avoid"] or "Iron" in output["limit"], "Expected Iron restriction for high Hemoglobin"
        assert "Added Sugar" in output["avoid"] or "Added Sugar" in output["limit"], "Expected Sugar restriction for high HbA1c"
        assert "Saturated Fat" in output["avoid"] or "Saturated Fat" in output["limit"], "Expected Saturated Fat restriction for high LDL"

        print("\n==========================================================")
        print("ALL KNOWLEDGE BASE AUTOMATED TESTS PASSED SUCCESSFULLY!")
        print("==========================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
