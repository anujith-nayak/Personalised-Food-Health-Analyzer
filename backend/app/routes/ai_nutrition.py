"""
AI Nutrition Assistant — Part 10
==================================
Handles the "Other" health condition that users can freely type.

Logic:
  1. Normalize the typed condition name.
  2. Check if it already exists in health_r.csv (case-insensitive fuzzy match).
     If YES → return the existing rule-based analysis (no AI call needed).
     If NO  → call Gemini (google-generativeai) or OpenAI to generate structured
              evidence-based dietary guidance.

The AI NEVER diagnoses disease. It only provides dietary recommendations.
The response is always wrapped in a medical disclaimer.

Endpoint:
  POST /ai-nutrition/query
  Body: { "condition": "Crohn's Disease", "nutrition": {...} }
  Returns: AINutritionResponse
"""
from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services import dataset_loader as dl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-nutrition", tags=["AI Nutrition Assistant"])

# ── Response schema ────────────────────────────────────────────────────────────

class AINutritionResponse(BaseModel):
    condition:            str
    summary:              str
    foods_to_avoid:       list[str]
    foods_to_prefer:      list[str]
    nutrients_to_limit:   list[str]
    nutrients_to_increase: list[str]
    healthy_alternatives: list[str]
    sample_meal:          str
    guideline_source:     str
    medical_disclaimer:   str
    source:               str   # "rule_engine" | "ai_generated" | "fallback"


# ── Request schema ─────────────────────────────────────────────────────────────

class AINutritionRequest(BaseModel):
    condition: str              # The free-text health condition entered by user
    nutrition: Optional[dict] = None  # Optional extracted nutrition from food label


# ── Condition existence check ─────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _known_conditions() -> set[str]:
    """Return lowercase set of all conditions in health_r.csv."""
    df = dl.health_r
    if df.empty:
        return set()
    return {c.lower().strip() for c in df["condition"].unique()}


def _condition_exists_in_csv(condition: str) -> bool:
    """Fuzzy check: condition is in health_r.csv (substring match both ways)."""
    c = condition.lower().strip()
    known = _known_conditions()
    # Exact match
    if c in known:
        return True
    # Substring match in either direction
    for known_c in known:
        if c in known_c or known_c in c:
            return True
    return False


def _normalize_condition(condition: str) -> str:
    """Return a cleaned title-case condition name."""
    return condition.strip().title()


# ── Rule-engine fallback ───────────────────────────────────────────────────────

def _get_rule_engine_response(condition: str) -> AINutritionResponse:
    """
    Pull dietary rules directly from health_r.csv for conditions that exist there.
    No AI call needed.
    """
    df = dl.health_r
    c = condition.lower().strip()
    mask = df["condition"].str.lower().str.strip().apply(
        lambda x: c in x or x in c
    )
    rows = df[mask & df["restriction_level"].isin(["strict", "moderate"])]

    foods_to_avoid    = []
    nutrients_to_limit = []
    guidelines        = set()

    for _, row in rows.iterrows():
        flag = str(row.get("ingredient_flag", "")).strip()
        nutrient = str(row.get("nutrient", "")).strip()
        reco = str(row.get("recommendation", "")).strip()
        src  = str(row.get("guideline_source", "")).strip()

        if flag and flag not in ("nan", "") and flag not in foods_to_avoid:
            foods_to_avoid.append(flag.replace("_", " ").title())
        if nutrient and nutrient not in nutrients_to_limit:
            nutrients_to_limit.append(nutrient.replace("_", " ").title())
        if src:
            guidelines.add(src)

    # Pull recommendations as foods_to_prefer from recommended_foods.csv
    rec_df = dl.recommended_foods
    rec_mask = rec_df["Condition"].str.lower().str.strip().apply(
        lambda x: c in x or x in c
    )
    foods_to_prefer = rec_df[rec_mask]["BetterAlternative"].dropna().tolist()

    return AINutritionResponse(
        condition=_normalize_condition(condition),
        summary=(
            f"Evidence-based dietary guidelines for {_normalize_condition(condition)} "
            f"sourced from {', '.join(list(guidelines)[:3]) or 'clinical guidelines'}."
        ),
        foods_to_avoid=list(dict.fromkeys(foods_to_avoid))[:8],
        foods_to_prefer=list(dict.fromkeys(foods_to_prefer))[:6],
        nutrients_to_limit=list(dict.fromkeys(nutrients_to_limit))[:6],
        nutrients_to_increase=["Fiber", "Potassium", "Magnesium", "Omega-3"],
        healthy_alternatives=foods_to_prefer[:5] or [
            "Fresh fruits", "Vegetables", "Whole grains",
            "Lean protein", "Low-fat dairy"
        ],
        sample_meal=(
            "Breakfast: Oats with fruits. "
            "Lunch: Dal, brown rice, salad. "
            "Dinner: Grilled vegetables with lean protein."
        ),
        guideline_source=", ".join(list(guidelines)) or "WHO/AHA/ADA",
        medical_disclaimer=(
            "This information is for educational purposes only and does not constitute "
            "medical advice. Please consult a registered dietitian or physician before "
            "making dietary changes for your health condition."
        ),
        source="rule_engine",
    )


# ── AI call ────────────────────────────────────────────────────────────────────

_AI_PROMPT_TEMPLATE = """
You are a registered dietitian providing evidence-based dietary guidance.
A user has the health condition: {condition}

Generate structured dietary recommendations in the following JSON format ONLY.
Do NOT diagnose, prescribe medication, or provide medical advice.
Only provide dietary/nutritional guidance backed by WHO, AHA, ADA, ICMR, or NHS guidelines.

{{
  "summary": "2-3 sentence dietary summary for this condition",
  "foods_to_avoid": ["food1", "food2", "food3", "food4", "food5"],
  "foods_to_prefer": ["food1", "food2", "food3", "food4", "food5"],
  "nutrients_to_limit": ["Sodium", "Sugar", "Saturated Fat"],
  "nutrients_to_increase": ["Fiber", "Potassium", "Omega-3"],
  "healthy_alternatives": ["alt1", "alt2", "alt3"],
  "sample_meal": "Breakfast: X. Lunch: Y. Dinner: Z.",
  "guideline_source": "WHO/AHA/ADA/ICMR/NHS"
}}

Respond with ONLY valid JSON. No explanations outside the JSON block.
"""

_DISCLAIMER = (
    "This AI-generated guidance is for educational purposes only and does not constitute "
    "medical advice or a medical diagnosis. Dietary needs vary by individual. "
    "Always consult a qualified healthcare professional or registered dietitian before "
    "making dietary changes for any health condition."
)


def _call_gemini(condition: str) -> dict | None:
    """Call Google Gemini API. Returns parsed dict or None on failure."""
    try:
        import google.generativeai as genai  # type: ignore
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("[AI] GEMINI_API_KEY not set")
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = _AI_PROMPT_TEMPLATE.format(condition=condition)
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Extract JSON block
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[AI] Gemini call failed: {e}")
        return None


def _call_openai(condition: str) -> dict | None:
    """Call OpenAI API. Returns parsed dict or None on failure."""
    try:
        from openai import OpenAI  # type: ignore
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("[AI] OPENAI_API_KEY not set")
            return None
        client = OpenAI(api_key=api_key)
        prompt = _AI_PROMPT_TEMPLATE.format(condition=condition)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a registered dietitian. Respond in valid JSON only."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
        )
        raw = completion.choices[0].message.content.strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[AI] OpenAI call failed: {e}")
        return None


def _fallback_response(condition: str) -> AINutritionResponse:
    """Return a generic safe response when AI is unavailable."""
    return AINutritionResponse(
        condition=_normalize_condition(condition),
        summary=(
            f"General dietary guidance for {_normalize_condition(condition)}. "
            "Please consult a dietitian for personalised advice."
        ),
        foods_to_avoid=["Ultra-processed foods", "Fried foods", "Sugary beverages",
                        "Excess salt", "Alcohol"],
        foods_to_prefer=["Fresh fruits", "Vegetables", "Whole grains",
                         "Lean protein", "Low-fat dairy"],
        nutrients_to_limit=["Saturated Fat", "Sodium", "Added Sugar"],
        nutrients_to_increase=["Fiber", "Potassium", "Omega-3", "Vitamins"],
        healthy_alternatives=["Oats", "Boiled vegetables", "Fruits",
                               "Lentils", "Plain yogurt"],
        sample_meal=(
            "Breakfast: Oats with banana. "
            "Lunch: Dal rice with salad. "
            "Dinner: Grilled vegetables with chapati."
        ),
        guideline_source="WHO/ICMR General Guidelines",
        medical_disclaimer=_DISCLAIMER,
        source="fallback",
    )


# ── Route ──────────────────────────────────────────────────────────────────────

@router.post("/query", response_model=AINutritionResponse)
async def query_ai_nutrition(
    request: AINutritionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Query dietary guidance for any health condition.

    - If the condition exists in health_r.csv → returns rule-based analysis instantly.
    - If not → calls Gemini or OpenAI for AI-generated structured guidance.
    - Always includes a medical disclaimer.
    - Never diagnoses diseases or recommends medication.
    """
    condition = request.condition.strip()
    if not condition or len(condition) < 2:
        raise HTTPException(status_code=400, detail="Please provide a valid health condition.")

    if len(condition) > 200:
        raise HTTPException(status_code=400, detail="Condition name too long.")

    logger.info(f"[AI-Nutrition] Query for: '{condition}' by user {current_user.id}")

    # ── Step 1: Check rule engine first ────────────────────────────────────
    if _condition_exists_in_csv(condition):
        logger.info(f"[AI-Nutrition] '{condition}' found in rule engine — skipping AI")
        return _get_rule_engine_response(condition)

    # ── Step 2: Try Gemini ─────────────────────────────────────────────────
    logger.info(f"[AI-Nutrition] '{condition}' not in dataset — calling AI")
    result = _call_gemini(condition)

    # ── Step 3: Fallback to OpenAI if Gemini fails ─────────────────────────
    if result is None:
        result = _call_openai(condition)

    # ── Step 4: Fallback response if both fail ─────────────────────────────
    if result is None:
        logger.warning(f"[AI-Nutrition] Both AI providers failed for '{condition}'")
        return _fallback_response(condition)

    # ── Step 5: Parse and return AI result ────────────────────────────────
    return AINutritionResponse(
        condition=_normalize_condition(condition),
        summary=result.get("summary", ""),
        foods_to_avoid=result.get("foods_to_avoid", [])[:8],
        foods_to_prefer=result.get("foods_to_prefer", [])[:6],
        nutrients_to_limit=result.get("nutrients_to_limit", [])[:6],
        nutrients_to_increase=result.get("nutrients_to_increase", [])[:6],
        healthy_alternatives=result.get("healthy_alternatives", [])[:5],
        sample_meal=result.get("sample_meal", ""),
        guideline_source=result.get("guideline_source", "AI-Generated"),
        medical_disclaimer=_DISCLAIMER,
        source="ai_generated",
    )
