"""
DB-driven food restriction engine.

Rules are loaded from the food_restriction_rules table.
On first startup, seed_rules() populates default rules if the table is empty.
To add a new disease: INSERT a row into food_restriction_rules — no code change needed.

Key design decisions:
  - BP and Sugar have SEPARATE rules for low / normal / high
  - Normal status → NO restrictions
  - Current health conditions (Fever, Cold, etc.) have their own categories
  - Output is grouped by category, not a flat list
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.user import HealthProfile

# ── Default rules seeded into DB on first startup ────────────────────────────

DEFAULT_RULES: list[dict] = [
    # ── Hypertension ──────────────────────────────────────────────────────────
    {
        "condition_key": "hypertension_high",
        "category_label": "High BP",
        "foods": [
            "Chips", "Papad", "Pickles", "Instant Noodles",
            "Processed Meats (Sausage, Salami)", "Packaged Soups",
            "Salted Butter", "Canned Foods", "Fast Food", "Salted Nuts",
            "Soy Sauce", "Namkeen / Salty Snacks",
        ],
    },
    {
        "condition_key": "hypertension_low",
        "category_label": "Low BP",
        "foods": [
            "Alcohol", "Large Carbohydrate Meals (cause BP drop)",
            "Caffeine in excess", "Diuretic foods in excess",
        ],
    },
    # Normal BP → no entry (no restrictions)

    # ── Diabetes ──────────────────────────────────────────────────────────────
    {
        "condition_key": "diabetes_high",
        "category_label": "High Blood Sugar",
        "foods": [
            "Gulab Jamun", "Jalebi", "Cake", "Pastries",
            "Chocolate", "Ice Cream", "Sugary Drinks (Pepsi, Coke)",
            "Fruit Juices (packaged)", "White Bread", "White Rice (excess)",
            "Sweetened Cereals", "Cookies / Biscuits", "Candy / Toffee",
            "Sweetened Curd / Flavoured Yogurt",
        ],
    },
    {
        "condition_key": "diabetes_low",
        "category_label": "Low Blood Sugar",
        "foods": [
            "Skipping meals", "Excess alcohol on empty stomach",
            "High-fibre foods on empty stomach (can worsen hypoglycemia)",
        ],
    },
    # Normal sugar → no entry

    # ── PCOS ──────────────────────────────────────────────────────────────────
    {
        "condition_key": "pcos",
        "category_label": "PCOS",
        "foods": [
            "Sugary Drinks", "Jalebi", "Candy", "Packaged Juices",
            "Deep Fried Snacks (Samosa, Vada)", "Fast Food",
            "Refined Flour (Maida) Products", "Processed Foods",
            "Trans-fat Snacks", "Excessive Dairy",
        ],
    },

    # ── PCOD ──────────────────────────────────────────────────────────────────
    {
        "condition_key": "pcod",
        "category_label": "PCOD",
        "foods": [
            "Junk Food (Burger, Pizza)", "Packaged Chips",
            "Sugary Sweets", "Refined Carbohydrates",
            "Processed Meats", "Excess Caffeine",
            "Alcohol", "Artificial Sweeteners",
        ],
    },

    # ── Heart Disease ─────────────────────────────────────────────────────────
    {
        "condition_key": "heart_disease",
        "category_label": "Heart Disease",
        "foods": [
            "Fried Foods (Puri, Bhatura)", "Butter in excess",
            "Ghee in excess", "Red Meat", "Full-fat Dairy",
            "Packaged Baked Goods", "Trans-fat Spreads",
            "Salted Chips", "Fast Food", "Organ Meats (Liver)",
        ],
    },

    # ── Kidney Disease ────────────────────────────────────────────────────────
    {
        "condition_key": "kidney_disease",
        "category_label": "Kidney Disease",
        "foods": [
            "Chips / Salted Snacks", "Pickles", "Papad",
            "Processed Meats", "Packaged Soups (high sodium)",
            "Banana (high potassium)", "Oranges (high potassium)",
            "Tomato Sauce / Ketchup", "Dark Colas",
            "Nuts in excess (high phosphorus)", "Whole Wheat Bread (high phosphorus)",
        ],
    },

    # ── Thyroid ───────────────────────────────────────────────────────────────
    {
        "condition_key": "thyroid_hypothyroidism",
        "category_label": "Hypothyroidism",
        "foods": [
            "Raw Cabbage in excess", "Raw Cauliflower in excess",
            "Raw Broccoli in excess", "Soy Milk / Tofu (excess)",
            "Processed Foods", "Gluten (if sensitive)",
            "Excess Coffee / Tea near medication time",
        ],
    },
    {
        "condition_key": "thyroid_hyperthyroidism",
        "category_label": "Hyperthyroidism",
        "foods": [
            "Iodised Salt (excess)", "Seafood in excess",
            "Dairy in large amounts", "Caffeine",
            "Spicy Foods", "Alcohol",
        ],
    },

    # ── Obesity ───────────────────────────────────────────────────────────────
    {
        "condition_key": "obesity",
        "category_label": "Obesity",
        "foods": [
            "Sugary Beverages", "Cold Drinks / Soda",
            "Fried Snacks", "Fast Food", "Ice Cream",
            "Cake / Pastries", "Processed / Packaged Foods",
            "Mayonnaise / Creamy Sauces", "White Bread",
            "High-Calorie Desserts",
        ],
    },

    # ── High Cholesterol ──────────────────────────────────────────────────────
    {
        "condition_key": "high_cholesterol",
        "category_label": "High Cholesterol",
        "foods": [
            "Butter / Ghee in excess", "Red Meat (Beef, Pork, Lamb)",
            "Full-fat Dairy (Cream, Cheese)", "Fried Foods",
            "Processed Meats (Sausage, Salami, Hot Dogs)",
            "Trans-fat Baked Goods (Biscuits, Pastries)",
            "Coconut Oil / Palm Oil in excess",
            "Egg Yolks in excess", "Organ Meats (Liver)",
            "Fast Food", "Packaged Snacks",
        ],
    },

    # ── Appendicitis (Acute) ───────────────────────────────────────────────────
    {
        "condition_key": "appendicitis_acute",
        "category_label": "Appendicitis (Acute Phase)",
        "foods": [
            "Raw Vegetables", "High-Fibre Foods (Beans, Lentils, Whole Grains)",
            "Fried / Oily Foods", "Spicy Foods",
            "Red Meat", "Dairy in large amounts",
            "Carbonated Drinks", "Alcohol",
            "Caffeinated Beverages", "Processed Snacks",
            "Seeds and Nuts", "Large Meals",
        ],
    },

    # ── Appendicitis (Recovery) ────────────────────────────────────────────────
    {
        "condition_key": "appendicitis_recovery",
        "category_label": "Appendicitis (Recovery Phase)",
        "foods": [
            "Fried / Oily Foods", "Spicy Foods",
            "Alcohol", "Carbonated Drinks",
            "Raw Vegetables (first 2 weeks)", "Whole Seeds and Nuts",
            "Very High-Fibre Foods in first week", "Heavy Meats",
            "Fast Food", "Processed Snacks",
        ],
    },

    # ── Current Health Conditions ─────────────────────────────────────────────
    {
        "condition_key": "fever",
        "category_label": "Fever",
        "foods": [
            "Ice Cream", "Cold Drinks / Cold Water",
            "Refrigerated Juices", "Cold Curd / Raita",
            "Fried Foods", "Oily Curries",
            "Raw Salads", "Spicy Food",
        ],
    },
    {
        "condition_key": "cold",
        "category_label": "Cold",
        "foods": [
            "Ice Cream", "Cold Water / Cold Drinks",
            "Refrigerated Foods", "Banana (aggravates mucus)",
            "Dairy (thickens mucus)", "Fried Snacks",
            "Sugary Foods",
        ],
    },
    {
        "condition_key": "cough",
        "category_label": "Cough",
        "foods": [
            "Ice Cream", "Cold Drinks", "Cold Water",
            "Fried Foods", "Spicy Foods",
            "Sugary Sweets", "Packaged Juices",
        ],
    },
    {
        "condition_key": "diarrhea",
        "category_label": "Diarrhea",
        "foods": [
            "Fried Foods", "Spicy Curries",
            "Milk / Dairy (if lactose intolerant)",
            "Street Food", "Caffeine (Tea / Coffee)",
            "Alcohol", "Raw Vegetables",
            "High-Fibre Foods (beans, lentils)",
            "Sugary Foods",
        ],
    },
    {
        "condition_key": "stomach_upset",
        "category_label": "Stomach Upset",
        "foods": [
            "Spicy Foods", "Fried / Oily Foods",
            "Acidic Foods (Citrus, Tomato)",
            "Carbonated Drinks", "Alcohol",
            "Raw Onion / Garlic", "Dairy (if sensitive)",
        ],
    },
    {
        "condition_key": "vomiting",
        "category_label": "Vomiting",
        "foods": [
            "Spicy Foods", "Fried Foods", "Dairy",
            "Caffeine", "Alcohol",
            "Strong-smelling Foods", "Sugary Foods",
        ],
    },
    {
        "condition_key": "headache",
        "category_label": "Headache",
        "foods": [
            "Aged Cheese", "Red Wine", "Chocolate",
            "Caffeine in excess", "Processed Meats (nitrates)",
            "MSG-containing Foods", "Alcohol",
            "Artificial Sweeteners (Aspartame)",
        ],
    },
    {
        "condition_key": "weakness",
        "category_label": "Weakness",
        "foods": [
            "Sugary Snacks (cause energy crash)",
            "Alcohol", "Caffeine in excess",
            "Processed / Junk Food",
            "Skipping meals",
        ],
    },
]

# ── Validation ranges ─────────────────────────────────────────────────────────

BP_RANGES = {
    "low":    {"systolic": (0, 89),   "diastolic": (0, 59)},
    "normal": {"systolic": (90, 120), "diastolic": (60, 80)},
    "high":   {"systolic": (121, 300), "diastolic": (81, 200)},
}

SUGAR_RANGES = {
    "low":    {"fasting": (0, 69),    "post_meal": (0, 79)},
    "normal": {"fasting": (70, 99),   "post_meal": (80, 139)},
    "high":   {"fasting": (100, 600), "post_meal": (140, 600)},
}


def validate_bp(status: str, systolic: int | None, diastolic: int | None) -> str | None:
    """Returns error string if values don't match selected status, else None."""
    if status == "normal" or (systolic is None and diastolic is None):
        return None
    r = BP_RANGES.get(status, {})
    if systolic is not None:
        lo, hi = r.get("systolic", (0, 999))
        if not (lo <= systolic <= hi):
            return f"Systolic {systolic} mmHg does not match '{status}' range ({lo}–{hi}). Please correct the value or change the status."
    if diastolic is not None:
        lo, hi = r.get("diastolic", (0, 999))
        if not (lo <= diastolic <= hi):
            return f"Diastolic {diastolic} mmHg does not match '{status}' range ({lo}–{hi}). Please correct the value or change the status."
    return None


def validate_sugar(status: str, fasting: float | None, post_meal: float | None) -> str | None:
    """Returns error string if values don't match selected status, else None."""
    if status == "normal" or (fasting is None and post_meal is None):
        return None
    r = SUGAR_RANGES.get(status, {})
    if fasting is not None:
        lo, hi = r.get("fasting", (0, 9999))
        if not (lo <= fasting <= hi):
            return f"Fasting sugar {fasting} does not match '{status}' range ({lo}–{hi}). Please correct the value or change the status."
    if post_meal is not None:
        lo, hi = r.get("post_meal", (0, 9999))
        if not (lo <= post_meal <= hi):
            return f"Post-meal sugar {post_meal} does not match '{status}' range ({lo}–{hi}). Please correct the value or change the status."
    return None


# ── Status name → condition_key mapping ──────────────────────────────────────

STATUS_KEY_MAP = {
    "Fever":          "fever",
    "Cold":           "cold",
    "Cough":          "cough",
    "Diarrhea":       "diarrhea",
    "Stomach Upset":  "stomach_upset",
    "Vomiting":       "vomiting",
    "Headache":       "headache",
    "Weakness":       "weakness",
}


# ── Rule loader / seeder ──────────────────────────────────────────────────────

def seed_rules(db: "Session") -> None:
    """Insert default rules into DB if any are missing. Idempotent per condition_key."""
    from app.models.user import FoodRestrictionRule
    existing_keys = {r.condition_key for r in db.query(FoodRestrictionRule).all()}
    added = 0
    for rule in DEFAULT_RULES:
        if rule["condition_key"] not in existing_keys:
            db.add(FoodRestrictionRule(
                condition_key=rule["condition_key"],
                category_label=rule["category_label"],
                foods_json=rule["foods"],
            ))
            added += 1
    if added > 0:
        db.commit()
        print(f"[FoodRestrictions] Seeded {added} new rule(s).")


def _get_rule(db: "Session", key: str) -> tuple[str, list[str]] | None:
    """Fetch (category_label, foods) for a condition_key from DB."""
    from app.models.user import FoodRestrictionRule
    rule = db.query(FoodRestrictionRule).filter(
        FoodRestrictionRule.condition_key == key
    ).first()
    if rule:
        return rule.category_label, rule.foods_json
    return None


def generate_grouped_restrictions(
    profile: "HealthProfile",
    current_statuses: list[str],
    db: "Session",
) -> list[dict]:
    """
    Return a list of category groups, each with label + items.
    Format: [{"category": "High BP", "items": ["Chips", ...]}, ...]
    Deduplication is applied within each group.
    """
    groups: list[dict] = []
    seen_keys: set[str] = set()

    def add_group(key: str) -> None:
        if key in seen_keys:
            return
        seen_keys.add(key)
        result = _get_rule(db, key)
        if result:
            label, foods = result
            if foods:
                groups.append({"category": label, "items": foods})

    # ── Hypertension (severity-aware) ─────────────────────────────────────
    if profile.hypertension and profile.bp_status:
        if profile.bp_status != "normal":
            add_group(f"hypertension_{profile.bp_status}")

    # ── Diabetes (severity-aware) ─────────────────────────────────────────
    if profile.diabetes and profile.sugar_status:
        if profile.sugar_status != "normal":
            add_group(f"diabetes_{profile.sugar_status}")

    # ── Thyroid (type-aware) ──────────────────────────────────────────────
    if profile.thyroid and profile.thyroid_type:
        add_group(f"thyroid_{profile.thyroid_type}")

    # ── Other chronic conditions ──────────────────────────────────────────
    for key in ["pcos", "pcod", "heart_disease", "kidney_disease",
                "obesity", "high_cholesterol"]:
        if getattr(profile, key, False):
            add_group(key)

    # ── Appendicitis (phase-aware) ────────────────────────────────────────
    if getattr(profile, "appendicitis", False):
        phase = (getattr(profile, "appendicitis_phase", None) or "").lower()
        if "acute" in phase:
            add_group("appendicitis_acute")
        elif "recovery" in phase or "post" in phase:
            add_group("appendicitis_recovery")
        else:
            add_group("appendicitis_acute")   # safe default

    # ── Current health statuses ───────────────────────────────────────────
    for status in current_statuses:
        key = STATUS_KEY_MAP.get(status)
        if key:
            add_group(key)

    return groups
