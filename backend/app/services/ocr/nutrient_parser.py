"""
RapidFuzz + Spatial Position Multi-Column Nutrient Parser.

Single canonical nutrition parsing implementation using spatial line/column coordinates,
RapidFuzz similarity matching against nutrient_aliases.json, and strict physiological validation.

Features:
  1. Header & X-Column Detection (Per 100g, Per serve, %GDA).
  2. Multi-word priority alias matching (Added Sugars before Sugar, Saturated/Trans Fat before Total Fat).
  3. Strict Y-coordinate row association — eliminates cross-row/cross-nutrient contamination.
  4. Zero hallucination — absent nutrients remain null / Not Available.
  5. Dual-column extraction (Per 100g and Per Serving) with explicit value_basis metadata.
"""

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from rapidfuzz import fuzz

from app.services.ocr.base import OCRResult, OCRLine

logger = logging.getLogger(__name__)

# Sanity range constraints (min, max) for physiological validation per serving / per 100g
SANITY_RANGES: Dict[str, Tuple[float, float]] = {
    "calories":      (0.0, 2000.0),
    "total_fat":     (0.0,  200.0),
    "saturated_fat": (0.0,  100.0),
    "trans_fat":     (0.0,   20.0),
    "cholesterol":   (0.0, 1500.0),
    "sodium":        (0.0, 5000.0),  # mg
    "carbohydrates": (0.0,  300.0),
    "sugar":         (0.0,  200.0),
    "added_sugar":   (0.0,  200.0),
    "fiber":         (0.0,   80.0),
    "protein":       (0.0,  200.0),
    "potassium":     (0.0, 6000.0),  # mg
    "calcium":       (0.0, 3000.0),  # mg
    "iron":          (0.0,  150.0),  # mg
    "serving_size":  (0.1, 2000.0),
}

# Core target nutrients required for high confidence
CORE_TARGET_NUTRIENTS = [
    "calories", "total_fat", "saturated_fat", "sodium", "carbohydrates", "sugar", "protein"
]

_ALIASES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "nutrient_aliases.json"
)


def load_nutrient_aliases() -> Dict[str, Dict[str, Any]]:
    """Loads nutrient alias registry from JSON configuration file."""
    path = os.path.abspath(_ALIASES_PATH)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    logger.warning(f"[PARSER] Config file not found at {path}, using default aliases.")
    return {}


class NutrientParser:
    """
    RapidFuzz & Spatial Column/Row Nutrient Parser.
    Strictly associates numbers on the same Y-row with nutrient names on the left.
    Separates Per 100g, Per Serve, and %GDA columns without cross-row contamination.
    """

    def __init__(self, alias_config: Optional[Dict[str, Dict[str, Any]]] = None, fuzzy_threshold: float = 78.0):
        self.aliases = alias_config or load_nutrient_aliases()
        self.fuzzy_threshold = fuzzy_threshold
        self._build_ordered_alias_list()

    def _build_ordered_alias_list(self):
        """
        Builds flat list of (alias_phrase, canonical_key) sorted by length descending
        so multi-word nutrients (Added Sugars, Saturated Fat, Trans Fat) are always matched
        BEFORE generic single-word keywords (Sugar, Fat).
        """
        alias_items = []
        for key, info in self.aliases.items():
            for alias in info.get("aliases", []):
                alias_items.append((alias.lower().strip(), key))

        # Multi-word first
        self.ordered_aliases = sorted(alias_items, key=lambda x: (len(x[0].split()), len(x[0])), reverse=True)

    def parse(self, ocr_result: OCRResult) -> Dict[str, Any]:
        """
        Parses OCRResult into dual-column structured nutrition data (Per 100g & Per Serving).
        Guarantees zero cross-row contamination and zero hallucinated values.
        """
        lines = ocr_result.lines
        raw_text = ocr_result.raw_text

        if not lines and raw_text:
            lines = [OCRLine(text=txt.strip(), confidence=0.7) for txt in raw_text.split("\n") if txt.strip()]

        # Step 1: Spatial sorting top-to-bottom, left-to-right
        sorted_lines = self._sort_lines_spatially(lines)

        # Step 2: Group lines into tight Y-coordinate rows (tolerance = 14px)
        spatial_rows = self._group_lines_into_rows(sorted_lines)

        # Step 3: Detect serving size (g) from header text (e.g. "Serving Size 12.5g")
        serving_size_g = self._extract_serving_size_g(sorted_lines, raw_text)

        # Step 4: Strict spatial row parsing for dual columns (per_100g, per_serving)
        extracted_dual = self._parse_spatial_table_rows(spatial_rows, serving_size_g)

        # Step 5: Validate physiological bounds and construct output dicts
        structured_facts, flat_per_100g, flat_per_serving = self._build_validated_dictionaries(
            extracted_dual, serving_size_g
        )

        # Step 6: Confidence calculation
        non_null_count = sum(1 for v in flat_per_serving.values() if v is not None)
        core_matched = sum(1 for k in CORE_TARGET_NUTRIENTS if flat_per_serving.get(k) is not None)

        ocr_conf = ocr_result.ocr_confidence
        parser_conf = round((core_matched / len(CORE_TARGET_NUTRIENTS)) * 100.0, 2)
        overall_conf = round((0.4 * ocr_conf) + (0.6 * parser_conf), 2)

        missing_nutrients = [k for k in self.aliases.keys() if flat_per_serving.get(k) is None]
        is_partial = len(missing_nutrients) > 0 and non_null_count > 0

        if non_null_count == 0:
            extraction_status = "parser_failed"
        elif core_matched < 2:
            extraction_status = "low_confidence"
        elif is_partial:
            extraction_status = "partial"
        else:
            extraction_status = "success"

        return {
            "serving_size_g": serving_size_g,
            "value_basis": "per_serving",
            "nutrition": flat_per_serving,           # canonical dict passed to evaluators
            "nutrition_per_100g": flat_per_100g,     # flat per 100g dict
            "nutrition_facts": structured_facts,     # rich dual-column structured dict
            "ocr_confidence": ocr_conf,
            "parser_confidence": parser_conf,
            "overall_confidence": overall_conf,
            "extraction_status": extraction_status,
            "missing_nutrients": missing_nutrients,
            "is_partial": is_partial,
            "matched_nutrient_names": [k for k, v in flat_per_serving.items() if v is not None],
            "is_fallback": ocr_result.is_fallback,
            "engine_name": ocr_result.engine_name,
        }

    def _sort_lines_spatially(self, lines: List[OCRLine]) -> List[OCRLine]:
        """Sorts lines top-to-bottom by Y coordinate, left-to-right by X coordinate."""
        def line_key(l: OCRLine):
            if l.bbox and len(l.bbox) > 0:
                min_y = min(pt[1] for pt in l.bbox)
                min_x = min(pt[0] for pt in l.bbox)
                return (min_y, min_x)
            return (999999.0, 999999.0)

        return sorted(lines, key=line_key)

    def _group_lines_into_rows(self, sorted_lines: List[OCRLine]) -> List[List[OCRLine]]:
        """Groups text tokens into tight spatial Y-coordinate rows (Y tolerance = 14px)."""
        rows: List[List[OCRLine]] = []
        for line in sorted_lines:
            if not line.bbox:
                rows.append([line])
                continue

            line_y = sum(pt[1] for pt in line.bbox) / len(line.bbox)
            placed = False
            for row in rows:
                if row[0].bbox:
                    row_y = sum(pt[1] for pt in row[0].bbox) / len(row[0].bbox)
                    if abs(line_y - row_y) < 14.0:  # tight 14px row tolerance
                        row.append(line)
                        placed = True
                        break
            if not placed:
                rows.append([line])

        for row in rows:
            row.sort(key=lambda l: min(pt[0] for pt in l.bbox) if l.bbox else 0)

        return rows

    def _extract_serving_size_g(self, sorted_lines: List[OCRLine], raw_text: str) -> Optional[float]:
        """Extracts serving size in grams (e.g., '12.5g' or 'Serving Size: 30g')."""
        full_text = "\n".join(l.text for l in sorted_lines) if sorted_lines else raw_text

        # Pattern 1: Explicit "12.5 g" or "12.5g" near serving
        m = re.search(r"(?:serving|serve|portion)\s*size[^\d]*([\d\.]+)\s*(?:g|ml|oz)", full_text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

        # Pattern 2: "Per serve (12.5g)" or "Per 12.5g"
        m = re.search(r"per\s+(?:serve|serving)\s*\(?\s*([\d\.]+)\s*g\)?", full_text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

        # Pattern 3: Bare "12.5g" or "30g" after serving keyword
        m = re.search(r"serving[^\d\n]*([\d\.]+)\s*g", full_text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

        return None

    def _parse_spatial_table_rows(
        self, spatial_rows: List[List[OCRLine]], serving_size_g: Optional[float]
    ) -> Dict[str, Dict[str, Optional[float]]]:
        """
        Parses each spatial row independently.
        Matches nutrient name on the left and extracts values for Per 100g and Per Serve.
        Strictly prevents cross-row contamination.
        """
        extracted: Dict[str, Dict[str, Optional[float]]] = {}

        for row in spatial_rows:
            if not row:
                continue

            row_text = " ".join(l.text for l in row).lower()

            # Skip header rows containing column labels
            if ("per 100g" in row_text or "per 100 g" in row_text) and ("per serve" in row_text or "per serving" in row_text):
                continue
            if "gda" in row_text or "daily value" in row_text:
                continue

            # Match nutrient alias against row text in priority order (multi-word first)
            matched_key = None
            matched_alias = None

            for alias_phrase, canonical_key in self.ordered_aliases:
                if canonical_key in extracted:
                    continue  # already extracted

                if canonical_key == "serving_size":
                    continue  # handled separately

                score = fuzz.partial_ratio(alias_phrase, row_text)
                if score >= self.fuzzy_threshold:
                    matched_key = canonical_key
                    matched_alias = alias_phrase
                    break

            if not matched_key:
                continue  # row is not a recognized nutrient row

            # Parse numeric tokens from THIS ROW ONLY (ignoring % / %GDA / %DV tokens)
            row_candidates = self._extract_row_numeric_tokens(row)

            if not row_candidates:
                continue  # no numeric values on this row

            val_100g, val_serve = self._assign_column_values(row_candidates, serving_size_g)

            if val_100g is not None or val_serve is not None:
                extracted[matched_key] = {
                    "per_100g": val_100g,
                    "per_serving": val_serve,
                }
                logger.info(
                    f"[PARSER] Matched row '{matched_alias}' -> {matched_key}: "
                    f"per_100g={val_100g}, per_serving={val_serve}"
                )

        return extracted

    def _extract_row_numeric_tokens(self, row: List[OCRLine]) -> List[Tuple[float, str, float]]:
        """
        Extracts non-% numeric tokens from a spatial row along with their X-coordinate.
        Returns list of (float_value, unit_string, center_x_coordinate).
        """
        candidates: List[Tuple[float, str, float]] = []

        for line in row:
            text = line.text.strip()
            # Calculate line center X
            if line.bbox and len(line.bbox) > 0:
                center_x = sum(pt[0] for pt in line.bbox) / len(line.bbox)
            else:
                center_x = 0.0

            tokens = text.split()
            for token in tokens:
                # Fix OCR artefact "Og" -> "0g"
                token_clean = re.sub(r"\b[Oo]g\b", "0g", token)

                # Skip percentage and %GDA / %DV tokens
                if "%" in token_clean or "gda" in token_clean.lower() or "dv" in token_clean.lower():
                    continue

                cleaned_num = re.sub(r"[^\d\.]", "", token_clean)
                if not cleaned_num or cleaned_num == ".":
                    continue

                try:
                    val = float(cleaned_num)
                    unit_str = re.sub(r"[\d\.]", "", token_clean).lower()
                    candidates.append((val, unit_str, center_x))
                except ValueError:
                    continue

        # Sort candidates left-to-right by X coordinate
        candidates.sort(key=lambda item: item[2])
        return candidates

    def _assign_column_values(
        self, candidates: List[Tuple[float, str, float]], serving_size_g: Optional[float]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Assigns numeric tokens to Per 100g and Per Serve columns based on X position / ordering.
        If table has 2 numeric columns:
          col 1 (left) = Per 100g
          col 2 (right) = Per Serve
        Computes missing column mathematically if serving_size_g is available.
        """
        if not candidates:
            return None, None

        val_100g: Optional[float] = None
        val_serve: Optional[float] = None

        if len(candidates) >= 2:
            # Column 1 = Per 100g, Column 2 = Per Serve
            val_100g = candidates[0][0]
            val_serve = candidates[1][0]
        elif len(candidates) == 1:
            val_100g = candidates[0][0]

        # Deduce missing column mathematically if serving_size_g is known
        if val_100g is not None and val_serve is None and serving_size_g and serving_size_g > 0:
            val_serve = round(val_100g * (serving_size_g / 100.0), 2)
        elif val_serve is not None and val_100g is None and serving_size_g and serving_size_g > 0:
            val_100g = round(val_serve * (100.0 / serving_size_g), 2)

        return val_100g, val_serve

    def _build_validated_dictionaries(
        self, extracted_dual: Dict[str, Dict[str, Optional[float]]], serving_size_g: Optional[float]
    ) -> Tuple[Dict[str, Any], Dict[str, Optional[float]], Dict[str, Optional[float]]]:
        """
        Applies unit normalization and SANITY_RANGES bounds checking.
        Returns:
          1. rich structured dual-column dict (per_100g, per_serving, unit)
          2. flat per_100g dict
          3. flat per_serving dict (canonical basis for health evaluators)
        Absent nutrients are strictly set to None / Not Available.
        """
        structured: Dict[str, Any] = {}
        flat_100g: Dict[str, Optional[float]] = {}
        flat_serve: Dict[str, Optional[float]] = {}

        standard_keys = [
            "calories", "total_fat", "saturated_fat", "trans_fat", "cholesterol",
            "sodium", "carbohydrates", "sugar", "added_sugar", "fiber", "protein",
            "potassium", "calcium", "iron"
        ]

        for key in standard_keys:
            data = extracted_dual.get(key)
            info = self.aliases.get(key, {})
            unit = info.get("unit", "g")

            if not data:
                structured[key] = None
                flat_100g[key] = None
                flat_serve[key] = None
                continue

            v_100g = data.get("per_100g")
            v_serve = data.get("per_serving")

            # Sanity range check
            min_val, max_val = SANITY_RANGES.get(key, (0.0, 99999.0))

            if v_100g is not None and not (min_val <= v_100g <= max_val):
                logger.warning(f"[PARSER] Rejected out-of-bounds per_100g value for {key}: {v_100g}")
                v_100g = None

            if v_serve is not None and not (min_val <= v_serve <= max_val):
                logger.warning(f"[PARSER] Rejected out-of-bounds per_serving value for {key}: {v_serve}")
                v_serve = None

            if v_100g is None and v_serve is None:
                structured[key] = None
                flat_100g[key] = None
                flat_serve[key] = None
            else:
                structured[key] = {
                    "per_100g": v_100g,
                    "per_serving": v_serve,
                    "unit": unit,
                }
                flat_100g[key] = v_100g
                flat_serve[key] = v_serve

        if serving_size_g:
            structured["serving_size"] = {
                "per_100g": 100.0,
                "per_serving": serving_size_g,
                "unit": "g",
            }
            flat_100g["serving_size"] = 100.0
            flat_serve["serving_size"] = serving_size_g
        else:
            flat_100g["serving_size"] = None
            flat_serve["serving_size"] = None

        return structured, flat_100g, flat_serve
