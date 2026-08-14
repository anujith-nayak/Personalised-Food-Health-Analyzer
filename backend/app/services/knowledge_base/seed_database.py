"""
Seed Database Utility for Evidence-Based Nutrition Knowledge Base
===================================================================
Seeds the SQLite database with reference ranges, parameter conditions,
evidence-based nutrition actions, food examples, and scientific citations.
"""

import logging
from sqlalchemy.orm import Session
from app.services.knowledge_base.database import (
    init_kb_db,
    KBSessionLocal,
    BloodParameter,
    BloodParameterCondition,
    NutritionAction,
    FoodExample,
    Reference,
)

logger = logging.getLogger(__name__)

# ── Scientific References ─────────────────────────────────────────────────────
REFERENCES_DATA = [
    {
        "evidence_source": "NIH",
        "organization": "National Institutes of Health (NIH)",
        "guideline": "NIH Office of Dietary Supplements Health Professional Fact Sheets",
        "url": "https://ods.od.nih.gov/factsheets/MVTE-HealthProfessional/",
    },
    {
        "evidence_source": "WHO",
        "organization": "World Health Organization (WHO)",
        "guideline": "WHO Healthy Diet Guidelines & Salt Reduction Recommendations",
        "url": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
    },
    {
        "evidence_source": "ADA",
        "organization": "American Diabetes Association (ADA)",
        "guideline": "ADA Standards of Care in Diabetes — Nutrition & Glycemic Control",
        "url": "https://diabetes.org/healthy-living/recipes-nutrition",
    },
    {
        "evidence_source": "AHA",
        "organization": "American Heart Association (AHA)",
        "guideline": "AHA Dietary Guidelines for Cardiovascular Disease Risk Reduction",
        "url": "https://www.heart.org/en/healthy-living/healthy-eating",
    },
    {
        "evidence_source": "NKF",
        "organization": "National Kidney Foundation (NKF)",
        "guideline": "NKF KDOQI Clinical Practice Guideline for Nutrition in CKD",
        "url": "https://www.kidney.org/atoz/content/nutri_ckd",
    },
]

# ── Blood Parameters ──────────────────────────────────────────────────────────
BLOOD_PARAMETERS_DATA = [
    {
        "parameter_name": "Hemoglobin",
        "display_name": "Hemoglobin",
        "normal_low": 13.5,
        "normal_high": 17.5,
        "unit": "g/dL",
        "description": "Oxygen-carrying protein in red blood cells.",
    },
    {
        "parameter_name": "HbA1c",
        "display_name": "HbA1c (Glycated Hemoglobin)",
        "normal_low": 4.0,
        "normal_high": 5.6,
        "unit": "%",
        "description": "Average blood sugar level over the past 2-3 months.",
    },
    {
        "parameter_name": "Fasting Blood Sugar",
        "display_name": "Fasting Glucose",
        "normal_low": 70.0,
        "normal_high": 99.0,
        "unit": "mg/dL",
        "description": "Blood glucose measured after an 8-hour fast.",
    },
    {
        "parameter_name": "Random Blood Sugar",
        "display_name": "Random Glucose",
        "normal_low": 70.0,
        "normal_high": 140.0,
        "unit": "mg/dL",
        "description": "Blood glucose measured at any random time.",
    },
    {
        "parameter_name": "LDL",
        "display_name": "LDL Cholesterol",
        "normal_low": 0.0,
        "normal_high": 100.0,
        "unit": "mg/dL",
        "description": "Low-density lipoprotein cholesterol ('bad' cholesterol).",
    },
    {
        "parameter_name": "HDL",
        "display_name": "HDL Cholesterol",
        "normal_low": 40.0,
        "normal_high": 100.0,
        "unit": "mg/dL",
        "description": "High-density lipoprotein cholesterol ('good' cholesterol).",
    },
    {
        "parameter_name": "Total Cholesterol",
        "display_name": "Total Cholesterol",
        "normal_low": 125.0,
        "normal_high": 200.0,
        "unit": "mg/dL",
        "description": "Overall measure of blood cholesterol levels.",
    },
    {
        "parameter_name": "Triglycerides",
        "display_name": "Triglycerides",
        "normal_low": 0.0,
        "normal_high": 150.0,
        "unit": "mg/dL",
        "description": "Type of fat (lipid) found in the blood.",
    },
    {
        "parameter_name": "Creatinine",
        "display_name": "Serum Creatinine",
        "normal_low": 0.7,
        "normal_high": 1.3,
        "unit": "mg/dL",
        "description": "Waste product excreted by kidneys; indicator of renal function.",
    },
    {
        "parameter_name": "eGFR",
        "display_name": "eGFR (Estimated Glomerular Filtration Rate)",
        "normal_low": 90.0,
        "normal_high": 120.0,
        "unit": "mL/min/1.73m2",
        "description": "Key indicator of how well kidneys filter waste from blood.",
    },
    {
        "parameter_name": "Potassium",
        "display_name": "Serum Potassium",
        "normal_low": 3.5,
        "normal_high": 5.0,
        "unit": "mEq/L",
        "description": "Essential electrolyte for muscle and heart function.",
    },
    {
        "parameter_name": "Sodium",
        "display_name": "Serum Sodium",
        "normal_low": 135.0,
        "normal_high": 145.0,
        "unit": "mEq/L",
        "description": "Major extracellular electrolyte regulating fluid balance.",
    },
    {
        "parameter_name": "Calcium",
        "display_name": "Serum Calcium",
        "normal_low": 8.5,
        "normal_high": 10.5,
        "unit": "mg/dL",
        "description": "Mineral essential for bones, cardiac contraction, and nerves.",
    },
    {
        "parameter_name": "Iron",
        "display_name": "Serum Iron",
        "normal_low": 60.0,
        "normal_high": 170.0,
        "unit": "mcg/dL",
        "description": "Circulating iron needed for hemoglobin formation.",
    },
    {
        "parameter_name": "Ferritin",
        "display_name": "Serum Ferritin",
        "normal_low": 24.0,
        "normal_high": 336.0,
        "unit": "ng/mL",
        "description": "Protein that stores iron inside body tissues.",
    },
    {
        "parameter_name": "Vitamin D",
        "display_name": "25-Hydroxy Vitamin D",
        "normal_low": 30.0,
        "normal_high": 100.0,
        "unit": "ng/mL",
        "description": "Fat-soluble vitamin required for bone density and immunity.",
    },
    {
        "parameter_name": "Vitamin B12",
        "display_name": "Vitamin B12 (Cobalamin)",
        "normal_low": 200.0,
        "normal_high": 900.0,
        "unit": "pg/mL",
        "description": "Essential nutrient for red blood cell synthesis and brain function.",
    },
    {
        "parameter_name": "ALT",
        "display_name": "ALT (Alanine Aminotransferase)",
        "normal_low": 7.0,
        "normal_high": 56.0,
        "unit": "U/L",
        "description": "Liver enzyme; elevated levels indicate hepatic cell stress.",
    },
    {
        "parameter_name": "AST",
        "display_name": "AST (Aspartate Aminotransferase)",
        "normal_low": 10.0,
        "normal_high": 40.0,
        "unit": "U/L",
        "description": "Enzyme found in liver, heart, and muscle tissue.",
    },
    {
        "parameter_name": "Uric Acid",
        "display_name": "Serum Uric Acid",
        "normal_low": 3.5,
        "normal_high": 7.2,
        "unit": "mg/dL",
        "description": "Waste product from breakdown of purines in food.",
    },
]

# ── Parameter Conditions ──────────────────────────────────────────────────────
CONDITIONS_DATA = [
    {"parameter_name": "Hemoglobin", "condition_name": "High"},
    {"parameter_name": "Hemoglobin", "condition_name": "Low"},
    {"parameter_name": "HbA1c", "condition_name": "High"},
    {"parameter_name": "Fasting Blood Sugar", "condition_name": "High"},
    {"parameter_name": "Fasting Blood Sugar", "condition_name": "Low"},
    {"parameter_name": "Random Blood Sugar", "condition_name": "High"},
    {"parameter_name": "LDL", "condition_name": "High"},
    {"parameter_name": "HDL", "condition_name": "Low"},
    {"parameter_name": "Total Cholesterol", "condition_name": "High"},
    {"parameter_name": "Triglycerides", "condition_name": "High"},
    {"parameter_name": "Creatinine", "condition_name": "High"},
    {"parameter_name": "eGFR", "condition_name": "Low"},
    {"parameter_name": "Potassium", "condition_name": "High"},
    {"parameter_name": "Potassium", "condition_name": "Low"},
    {"parameter_name": "Sodium", "condition_name": "High"},
    {"parameter_name": "Sodium", "condition_name": "Low"},
    {"parameter_name": "Calcium", "condition_name": "Low"},
    {"parameter_name": "Calcium", "condition_name": "High"},
    {"parameter_name": "Iron", "condition_name": "Low"},
    {"parameter_name": "Iron", "condition_name": "High"},
    {"parameter_name": "Ferritin", "condition_name": "Low"},
    {"parameter_name": "Ferritin", "condition_name": "High"},
    {"parameter_name": "Vitamin D", "condition_name": "Low"},
    {"parameter_name": "Vitamin B12", "condition_name": "Low"},
    {"parameter_name": "ALT", "condition_name": "High"},
    {"parameter_name": "AST", "condition_name": "High"},
    {"parameter_name": "Uric Acid", "condition_name": "High"},
]

# ── Nutrition Actions ─────────────────────────────────────────────────────────
NUTRITION_ACTIONS_DATA = [
    {
        "parameter_name": "Hemoglobin",
        "condition_name": "High",
        "nutrient": "Iron",
        "action": "Limit",
        "severity": "High",
        "reason": "High hemoglobin may require limiting excessive iron intake until medically evaluated.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Hemoglobin",
        "condition_name": "Low",
        "nutrient": "Iron",
        "action": "Increase",
        "severity": "High",
        "reason": "Supports red blood cell production and oxygen transportation.",
        "evidence_source": "WHO",
    },
    {
        "parameter_name": "Hemoglobin",
        "condition_name": "Low",
        "nutrient": "Vitamin C",
        "action": "Increase",
        "severity": "Medium",
        "reason": "Vitamin C significantly enhances dietary non-heme iron absorption.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "HbA1c",
        "condition_name": "High",
        "nutrient": "Added Sugar",
        "action": "Avoid",
        "severity": "High",
        "reason": "High HbA1c indicates poor long-term glucose control.",
        "evidence_source": "ADA",
    },
    {
        "parameter_name": "HbA1c",
        "condition_name": "High",
        "nutrient": "Fiber",
        "action": "Increase",
        "severity": "High",
        "reason": "Dietary fiber slows carbohydrate absorption and improves glycemic control.",
        "evidence_source": "ADA",
    },
    {
        "parameter_name": "Fasting Blood Sugar",
        "condition_name": "High",
        "nutrient": "Added Sugar",
        "action": "Avoid",
        "severity": "High",
        "reason": "Elevated fasting blood sugar requires reducing simple sugar and glycemic load.",
        "evidence_source": "ADA",
    },
    {
        "parameter_name": "Fasting Blood Sugar",
        "condition_name": "High",
        "nutrient": "Fiber",
        "action": "Increase",
        "severity": "Medium",
        "reason": "Helps stabilize blood glucose spike after meals.",
        "evidence_source": "ADA",
    },
    {
        "parameter_name": "Random Blood Sugar",
        "condition_name": "High",
        "nutrient": "Added Sugar",
        "action": "Avoid",
        "severity": "High",
        "reason": "Random blood glucose above range indicates acute glycemic stress.",
        "evidence_source": "ADA",
    },
    {
        "parameter_name": "LDL",
        "condition_name": "High",
        "nutrient": "Saturated Fat",
        "action": "Avoid",
        "severity": "High",
        "reason": "Reduces LDL cholesterol and cardiovascular plaque accumulation.",
        "evidence_source": "AHA",
    },
    {
        "parameter_name": "LDL",
        "condition_name": "High",
        "nutrient": "Soluble Fiber",
        "action": "Increase",
        "severity": "High",
        "reason": "Soluble fiber binds cholesterol in the digestive system to reduce absorption.",
        "evidence_source": "AHA",
    },
    {
        "parameter_name": "HDL",
        "condition_name": "Low",
        "nutrient": "Omega-3 Fatty Acids",
        "action": "Increase",
        "severity": "Medium",
        "reason": "Healthy unsaturated fats help maintain and raise protective HDL levels.",
        "evidence_source": "AHA",
    },
    {
        "parameter_name": "Total Cholesterol",
        "condition_name": "High",
        "nutrient": "Saturated Fat",
        "action": "Limit",
        "severity": "High",
        "reason": "Helps manage overall circulating cholesterol concentration.",
        "evidence_source": "AHA",
    },
    {
        "parameter_name": "Triglycerides",
        "condition_name": "High",
        "nutrient": "Added Sugar",
        "action": "Limit",
        "severity": "High",
        "reason": "Excess simple carbohydrates and refined sugars elevate serum triglycerides.",
        "evidence_source": "AHA",
    },
    {
        "parameter_name": "Creatinine",
        "condition_name": "High",
        "nutrient": "Protein",
        "action": "Limit",
        "severity": "High",
        "reason": "May reduce kidney workload and nitrogenous metabolic waste build-up.",
        "evidence_source": "NKF",
    },
    {
        "parameter_name": "Creatinine",
        "condition_name": "High",
        "nutrient": "Sodium",
        "action": "Limit",
        "severity": "High",
        "reason": "Helps manage intraglomerular pressure and fluid balance in impaired kidney function.",
        "evidence_source": "NKF",
    },
    {
        "parameter_name": "eGFR",
        "condition_name": "Low",
        "nutrient": "Sodium",
        "action": "Limit",
        "severity": "High",
        "reason": "Low eGFR requires salt restriction to prevent fluid overload and hypertension.",
        "evidence_source": "NKF",
    },
    {
        "parameter_name": "eGFR",
        "condition_name": "Low",
        "nutrient": "Protein",
        "action": "Limit",
        "severity": "High",
        "reason": "Moderate protein intake helps preserve remaining nephron filtration capacity.",
        "evidence_source": "NKF",
    },
    {
        "parameter_name": "Potassium",
        "condition_name": "High",
        "nutrient": "Potassium",
        "action": "Limit",
        "severity": "High",
        "reason": "Hyperkalemia poses severe risk of cardiac dysrhythmias; restriction required.",
        "evidence_source": "NKF",
    },
    {
        "parameter_name": "Potassium",
        "condition_name": "Low",
        "nutrient": "Potassium",
        "action": "Increase",
        "severity": "High",
        "reason": "Supports normal vascular tone, nerve signaling, and cardiac contraction.",
        "evidence_source": "WHO",
    },
    {
        "parameter_name": "Sodium",
        "condition_name": "High",
        "nutrient": "Sodium",
        "action": "Limit",
        "severity": "High",
        "reason": "High serum sodium requires limiting dietary salt and sodium-rich packaged foods.",
        "evidence_source": "AHA",
    },
    {
        "parameter_name": "Calcium",
        "condition_name": "Low",
        "nutrient": "Calcium",
        "action": "Increase",
        "severity": "High",
        "reason": "Essential for maintaining structural bone density and muscular signaling.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Calcium",
        "condition_name": "Low",
        "nutrient": "Vitamin D",
        "action": "Increase",
        "severity": "High",
        "reason": "Vitamin D is essential for intestinal calcium absorption.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Iron",
        "condition_name": "Low",
        "nutrient": "Iron",
        "action": "Increase",
        "severity": "High",
        "reason": "Low serum iron requires replenishment to avoid microcytic anemia.",
        "evidence_source": "WHO",
    },
    {
        "parameter_name": "Iron",
        "condition_name": "High",
        "nutrient": "Iron",
        "action": "Limit",
        "severity": "High",
        "reason": "Excess iron accumulates in vital organs; avoid fortified foods and supplements.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Ferritin",
        "condition_name": "Low",
        "nutrient": "Iron",
        "action": "Increase",
        "severity": "High",
        "reason": "Low ferritin signifies depleted tissue iron storage reserves.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Ferritin",
        "condition_name": "High",
        "nutrient": "Iron",
        "action": "Limit",
        "severity": "High",
        "reason": "High ferritin indicates potential iron overload or systemic inflammation.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Vitamin D",
        "condition_name": "Low",
        "nutrient": "Vitamin D",
        "action": "Increase",
        "severity": "High",
        "reason": "Vitamin D insufficiency reduces bone mineral density and immune response.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Vitamin B12",
        "condition_name": "Low",
        "nutrient": "Vitamin B12",
        "action": "Increase",
        "severity": "High",
        "reason": "Required for nerve myelin sheath synthesis and red blood cell maturation.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "ALT",
        "condition_name": "High",
        "nutrient": "Saturated Fat",
        "action": "Limit",
        "severity": "Medium",
        "reason": "Limiting saturated fats reduces hepatic lipid accumulation and liver enzyme strain.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "AST",
        "condition_name": "High",
        "nutrient": "Alcohol",
        "action": "Avoid",
        "severity": "High",
        "reason": "Elevated liver enzymes require eliminating hepatotoxic substances.",
        "evidence_source": "WHO",
    },
    {
        "parameter_name": "Uric Acid",
        "condition_name": "High",
        "nutrient": "Purines",
        "action": "Avoid",
        "severity": "High",
        "reason": "Purine metabolism yields uric acid, exacerbating gout and renal stone risk.",
        "evidence_source": "NIH",
    },
    {
        "parameter_name": "Uric Acid",
        "condition_name": "High",
        "nutrient": "Fructose",
        "action": "Limit",
        "severity": "Medium",
        "reason": "Fructose phosphorylation consumes ATP and generates uric acid precursors.",
        "evidence_source": "NIH",
    },
]

# ── Food Examples ─────────────────────────────────────────────────────────────
FOOD_EXAMPLES_DATA = [
    # Iron
    {"nutrient": "Iron", "action": "Limit", "food_name": "Red Meat", "category": "Meat"},
    {"nutrient": "Iron", "action": "Limit", "food_name": "Liver", "category": "Organ Meat"},
    {"nutrient": "Iron", "action": "Limit", "food_name": "Iron Fortified Cereals", "category": "Processed Grains"},
    {"nutrient": "Iron", "action": "Increase", "food_name": "Spinach", "category": "Vegetables"},
    {"nutrient": "Iron", "action": "Increase", "food_name": "Beans & Lentils", "category": "Legumes"},
    {"nutrient": "Iron", "action": "Increase", "food_name": "Pumpkin Seeds", "category": "Seeds"},
    # Added Sugar / Sugar
    {"nutrient": "Added Sugar", "action": "Avoid", "food_name": "Soft Drinks", "category": "Beverages"},
    {"nutrient": "Added Sugar", "action": "Avoid", "food_name": "Candy & Sweets", "category": "Confectionery"},
    {"nutrient": "Added Sugar", "action": "Avoid", "food_name": "Pastries & Cakes", "category": "Bakery"},
    {"nutrient": "Added Sugar", "action": "Limit", "food_name": "Flavored Sugary Yogurts", "category": "Dairy"},
    {"nutrient": "Added Sugar", "action": "Limit", "food_name": "Sweetened Fruit Juices", "category": "Beverages"},
    # Fiber / Soluble Fiber
    {"nutrient": "Fiber", "action": "Increase", "food_name": "Oats & Oatmeal", "category": "Grains"},
    {"nutrient": "Fiber", "action": "Increase", "food_name": "Apple with Skin", "category": "Fruits"},
    {"nutrient": "Fiber", "action": "Increase", "food_name": "Chia Seeds", "category": "Seeds"},
    {"nutrient": "Soluble Fiber", "action": "Increase", "food_name": "Barley & Oats", "category": "Grains"},
    {"nutrient": "Soluble Fiber", "action": "Increase", "food_name": "Kidney Beans", "category": "Legumes"},
    # Saturated Fat
    {"nutrient": "Saturated Fat", "action": "Avoid", "food_name": "Palm Oil", "category": "Oils & Fats"},
    {"nutrient": "Saturated Fat", "action": "Avoid", "food_name": "Butter & Ghee", "category": "Dairy Fat"},
    {"nutrient": "Saturated Fat", "action": "Avoid", "food_name": "Fatty Processed Meats", "category": "Meat"},
    {"nutrient": "Saturated Fat", "action": "Limit", "food_name": "Full-Fat Cheese", "category": "Dairy"},
    # Protein
    {"nutrient": "Protein", "action": "Limit", "food_name": "Excess Red Meat", "category": "Meat"},
    {"nutrient": "Protein", "action": "Limit", "food_name": "Concentrated Whey Protein Shakes", "category": "Supplements"},
    {"nutrient": "Protein", "action": "Limit", "food_name": "Processed Sausage & Bacon", "category": "Processed Meat"},
    # Sodium
    {"nutrient": "Sodium", "action": "Limit", "food_name": "Canned Soups", "category": "Processed Foods"},
    {"nutrient": "Sodium", "action": "Limit", "food_name": "Salty Potato Chips", "category": "Snacks"},
    {"nutrient": "Sodium", "action": "Limit", "food_name": "Instant Noodles", "category": "Processed Grains"},
    # Potassium
    {"nutrient": "Potassium", "action": "Limit", "food_name": "Bananas", "category": "Fruits"},
    {"nutrient": "Potassium", "action": "Limit", "food_name": "Potatoes", "category": "Vegetables"},
    {"nutrient": "Potassium", "action": "Increase", "food_name": "Avocado", "category": "Fruits"},
    {"nutrient": "Potassium", "action": "Increase", "food_name": "Spinach", "category": "Vegetables"},
    # Vitamin D & B12
    {"nutrient": "Vitamin D", "action": "Increase", "food_name": "Salmon & Mackerel", "category": "Seafood"},
    {"nutrient": "Vitamin D", "action": "Increase", "food_name": "Fortified Dairy Milk", "category": "Dairy"},
    {"nutrient": "Vitamin B12", "action": "Increase", "food_name": "Eggs", "category": "Poultry"},
    {"nutrient": "Vitamin B12", "action": "Increase", "food_name": "Greek Yogurt", "category": "Dairy"},
    # Purines & Fructose
    {"nutrient": "Purines", "action": "Avoid", "food_name": "Organ Meats (Kidney/Liver)", "category": "Meat"},
    {"nutrient": "Purines", "action": "Avoid", "food_name": "Shellfish (Shrimp/Crab)", "category": "Seafood"},
    {"nutrient": "Fructose", "action": "Limit", "food_name": "High-Fructose Corn Syrup Sweets", "category": "Sweeteners"},
]


def seed_knowledge_base(db: Session = None):
    """Populate knowledge base SQLite database if empty."""
    init_kb_db()
    close_at_end = False
    if db is None:
        db = KBSessionLocal()
        close_at_end = True

    try:
        # Check if already seeded
        param_count = db.query(BloodParameter).count()
        if param_count > 0:
            logger.info(f"[KB Seed] Database already populated with {param_count} blood parameters.")
            return

        logger.info("[KB Seed] Seeding Evidence-Based Knowledge Base...")

        # 1. References
        for r in REFERENCES_DATA:
            db.add(Reference(**r))
        db.flush()

        # 2. Blood Parameters
        for bp in BLOOD_PARAMETERS_DATA:
            db.add(BloodParameter(**bp))
        db.flush()

        # 3. Conditions
        for cond in CONDITIONS_DATA:
            db.add(BloodParameterCondition(**cond))
        db.flush()

        # 4. Nutrition Actions
        for na in NUTRITION_ACTIONS_DATA:
            db.add(NutritionAction(**na))
        db.flush()

        # 5. Food Examples
        for fe in FOOD_EXAMPLES_DATA:
            db.add(FoodExample(**fe))

        db.commit()
        logger.info("[KB Seed] ✓ Evidence-Based Knowledge Base successfully seeded!")

    except Exception as e:
        db.rollback()
        logger.error(f"[KB Seed] Failed to seed database: {e}")
        raise e
    finally:
        if close_at_end:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_knowledge_base()
