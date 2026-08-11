"""
Blood Report Parser
===================
Parses structured OCR data (OCRResult / OCRLine objects with bounding boxes).
Supports spatial row grouping, alias matching, non-whitelist unlisted lab parameter extraction,
spatial result vs reference range differentiation, robust metadata filtering, and zero cross-row contamination.
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from rapidfuzz import fuzz

from app.services.ocr.base import OCRResult, OCRLine

logger = logging.getLogger(__name__)

_ALIASES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "blood_report_aliases.json"
)


def load_blood_report_aliases() -> Dict[str, Dict[str, Any]]:
    """Loads blood report alias registry from JSON configuration file."""
    path = os.path.abspath(_ALIASES_PATH)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    logger.warning(f"[BLOOD_PARSER] Config file not found at {path}")
    return {}


def normalize_parameter_key(name: str) -> str:
    """Generates a safe normalized key from parameter display name."""
    clean = re.sub(r"[^\w\s]", "", name).strip().lower()
    clean = re.sub(r"\s+", "_", clean)
    return clean or f"custom_param_{hash(name) % 10000}"


class SpatialRow:
    """Represents a single horizontal spatial line of OCR text blocks."""

    def __init__(self, y_min: float, y_max: float):
        self.y_min = y_min
        self.y_max = y_max
        self.lines: List[OCRLine] = []

    def get_center_y(self) -> float:
        return (self.y_min + self.y_max) / 2.0

    def can_include(self, y_min: float, y_max: float, tolerance: float = 40.0) -> bool:
        line_center = (y_min + y_max) / 2.0
        return abs(line_center - self.get_center_y()) <= tolerance

    def add_line(self, ocr_line: OCRLine):
        self.lines.append(ocr_line)
        if ocr_line.bbox:
            ys = [pt[1] for pt in ocr_line.bbox]
            self.y_min = min(self.y_min, min(ys))
            self.y_max = max(self.y_max, max(ys))

    def get_full_text(self) -> str:
        # Sort left-to-right by X coordinate
        def get_min_x(line: OCRLine) -> float:
            if line.bbox:
                return min(pt[0] for pt in line.bbox)
            return 0.0

        sorted_lines = sorted(self.lines, key=get_min_x)
        return " ".join([l.text.strip() for l in sorted_lines if l.text.strip()])


class BloodReportParser:
    """
    Spatial parser for blood lab reports.
    Groups OCR tokens by horizontal rows, matches aliases, extracts unlisted lab tests,
    and isolates observed numeric test results from reference ranges.
    """

    def __init__(self, config: Optional[Dict[str, Dict[str, Any]]] = None, fuzzy_threshold: float = 88.0):
        self.config = config or load_blood_report_aliases()
        self.fuzzy_threshold = fuzzy_threshold
        self._build_ordered_alias_list()

    def _build_ordered_alias_list(self):
        """Builds list of (alias_phrase, parameter_key) sorted multi-word first."""
        alias_items = []
        for key, info in self.config.items():
            for alias in info.get("aliases", []):
                alias_items.append((alias.lower().strip(), key))

        self.ordered_aliases = sorted(alias_items, key=lambda x: (len(x[0].split()), len(x[0])), reverse=True)

    def parse_ocr_result(self, ocr_result: OCRResult | List[OCRLine] | List[str]) -> List[Dict[str, Any]]:
        """
        Main entrypoint. Accepts OCRResult, list of OCRLine, or list of plain string lines.
        Returns list of extracted parameter dicts.
        """
        spatial_rows = self._build_spatial_rows(ocr_result)
        extracted_results: List[Dict[str, Any]] = []
        matched_keys: set = set()

        for row in spatial_rows:
            row_text = row.get_full_text().strip()
            if not row_text or self._is_metadata_line(row_text):
                continue

            # Step A: Try matching against known aliases first
            known_match = self._match_known_alias(row_text, matched_keys)

            if known_match:
                extracted_results.append(known_match)
                matched_keys.add(known_match["parameter_key"])
            else:
                # Step B: Non-whitelist extraction — check if row contains an unlisted lab parameter
                unlisted_match = self._match_unlisted_parameter(row_text, matched_keys)
                if unlisted_match:
                    extracted_results.append(unlisted_match)
                    matched_keys.add(unlisted_match["parameter_key"])

        return extracted_results

    def parse_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Backward compatible plain line list parser wrapper."""
        return self.parse_ocr_result(lines)

    def _build_spatial_rows(self, ocr_input: OCRResult | List[OCRLine] | List[str]) -> List[SpatialRow]:
        """Groups OCR line tokens into horizontal spatial rows using Y coordinates."""
        lines: List[OCRLine] = []

        if isinstance(ocr_input, OCRResult):
            lines = ocr_input.lines
        elif isinstance(ocr_input, list):
            for item in ocr_input:
                if isinstance(item, OCRLine):
                    lines.append(item)
                elif isinstance(item, str):
                    lines.append(OCRLine(text=item, confidence=1.0, bbox=None))

        rows: List[SpatialRow] = []

        for line in lines:
            if not line.text.strip():
                continue

            if not line.bbox:
                new_row = SpatialRow(len(rows) * 25.0, len(rows) * 25.0 + 15.0)
                new_row.add_line(line)
                rows.append(new_row)
                continue

            ys = [pt[1] for pt in line.bbox]
            y_min, y_max = min(ys), max(ys)

            placed = False
            for r in rows:
                if r.can_include(y_min, y_max):
                    r.add_line(line)
                    placed = True
                    break

            if not placed:
                new_row = SpatialRow(y_min, y_max)
                new_row.add_line(line)
                rows.append(new_row)

        return sorted(rows, key=lambda r: r.get_center_y())

    def _is_metadata_line(self, line_text: str) -> bool:
        """
        Filters out non-medical lines such as patient name, gender, dates, invoice,
        medical record numbers, report IDs, barcodes, or section titles.
        """
        line_lower = line_text.lower().strip()

        # Metadata keyword patterns
        metadata_keywords = [
            r"\bpatient\b", r"\bpatient\s+information\b", r"\bpatient\s+name\b", r"\bname\b",
            r"\bgender\b", r"\bsex\b", r"^\s*[fm]\s*$", r"^\s*male\s*$", r"^\s*female\s*$",
            r"\bdate\s+of\s+birth\b", r"\bdob\b", r"\bbirth\s+date\b",
            r"\bdate\s+of\s+test\b", r"\breport\s+date\b", r"\btest\s+date\b", r"\bcollection\b",
            r"\bmedical\s+record\s+number\b", r"\bmrn\b", r"\brecord\s+number\b",
            r"\bpatient\s+id\b", r"\blab\s+id\b", r"\bsample\s+id\b", r"\binvoice\b",
            r"\bbarcode\b", r"\bphone\b", r"\bmobile\b", r"\baddress\b",
            r"\breferring\s+doctor\b", r"\broutine\s+check-up\b", r"\bclinical\s+history\b",
            r"^\s*n\/a\s*$", r"^\s*test\s+results\b", r"^\s*department\s+of\b",
            r"^\s*test\s+result\s+reference\s*range\b", r"^\s*test\b", r"^\s*result\b",
            r"^\s*reference\s+range\b", r"^\s*report\b"
        ]

        for pat in metadata_keywords:
            if re.search(pat, line_lower):
                return True

        # Standalone date strings (e.g., April 8, 1993, February 12, 2023, 08/04/1993, 2023-02-12)
        date_patterns = [
            r"\b(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}\b",
            r"\b\d{4}[\/\.-]\d{1,2}[\/\.-]\d{1,2}\b",
            r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}\b"
        ]
        for d_pat in date_patterns:
            if re.search(d_pat, line_lower):
                return True

        # Standalone medical record numbers like "00-991-23" or "00-991" without medical parameter name
        if re.search(r"^\s*\d{2,4}-\d{2,4}(?:-\d{2,4})?\s*$", line_text):
            return True

        return False

    def _match_known_alias(self, line_text: str, matched_keys: set) -> Optional[Dict[str, Any]]:
        """Matches spatial row text against blood_report_aliases.json."""
        line_lower = line_text.lower()

        # Isolate parameter name candidate (text preceding the first number)
        m_num = re.search(r"\b(\d+\.?\d*)\b", line_text)
        name_part = line_lower[:m_num.start()].strip() if m_num else line_lower

        if not name_part:
            return None

        for alias_phrase, param_key in self.ordered_aliases:
            if param_key in matched_keys:
                continue

            # Priority match against parameter name candidate
            if len(alias_phrase) <= 6:
                matched = (alias_phrase == name_part) or bool(re.search(r"\b" + re.escape(alias_phrase) + r"\b", name_part))
            else:
                score = fuzz.ratio(alias_phrase, name_part)
                matched = (score >= self.fuzzy_threshold)

            if matched:
                val_info = self._extract_spatial_value_unit_range(line_text, alias_phrase)
                if val_info["value"] is not None:
                    # Unit disambiguation between MCH (pg) and MCHC (g/dL)
                    unit_lower = (val_info["unit"] or "").lower()
                    if param_key == "mchc" and unit_lower == "pg":
                        continue
                    if param_key == "mch" and unit_lower == "g/dl":
                        continue

                    param_config = self.config.get(param_key, {})
                    return {
                        "parameter_key": param_key,
                        "display_name": param_config.get("display_name", param_key.replace("_", " ").title()),
                        "value": val_info["value"],
                        "unit": val_info["unit"] or param_config.get("unit", ""),
                        "reference_range": val_info["reference_range"] or param_config.get("normal_range", ""),
                        "is_known_alias": True,
                    }
        return None

    def _match_unlisted_parameter(self, line_text: str, matched_keys: set) -> Optional[Dict[str, Any]]:
        """
        Extracts valid medical lab parameters NOT present in blood_report_aliases.json.
        Example: "Vitamin D  24.5  ng/mL  30 - 100"
        """
        # Find position of first observed numeric result in line
        m_num = re.search(r"\b(\d+\.?\d*)\b", line_text)
        if not m_num:
            return None

        num_start = m_num.start()
        raw_name = line_text[:num_start].strip()

        if not raw_name or len(raw_name) < 2 or self._is_metadata_line(raw_name):
            return None

        val_info = self._extract_spatial_value_unit_range(line_text, raw_name)
        if val_info["value"] is None:
            return None

        norm_key = normalize_parameter_key(raw_name)
        if norm_key in matched_keys:
            return None

        return {
            "parameter_key": norm_key,
            "display_name": raw_name,
            "value": val_info["value"],
            "unit": val_info["unit"] or "",
            "reference_range": val_info["reference_range"] or "",
            "is_known_alias": False,
        }

    def _extract_spatial_value_unit_range(
        self, line_text: str, alias_or_name: str
    ) -> Dict[str, Any]:
        """
        Extracts observed numeric test result, unit, and reference range from line text.
        Prevents reference range bounds from being misidentified as observed values.
        """
        # Step 1: Detect reference range pattern (e.g., "70 - 99", "< 200", "27.0 - 33.0", "4.0-5.6")
        ref_range = None
        range_match = re.search(r"(\d+\.?\d*\s*-\s*\d+\.?\d*|(?:\b[<>]=?\s*\d+\.?\d*))", line_text)
        line_for_value = line_text

        if range_match:
            ref_range = range_match.group(1).strip()
            # Remove reference range from value extraction string to avoid range bound contamination
            line_for_value = line_text[:range_match.start()] + " " + line_text[range_match.end():]

        # Step 2: Tokenize remaining string and filter out alias name words
        tokens = line_for_value.split()
        alias_tokens = set(alias_or_name.lower().split())

        valid_units = {"mg/dl", "%", "u/l", "g/dl", "meq/l", "ml/min", "pg", "fl", "g/l", "mill/cmm", "thou/cmm", "10^3/ul", "ng/ml"}

        numeric_tokens = []
        unit_found = None

        for idx, token in enumerate(tokens):
            token_clean = token.lower().strip()
            if token_clean in alias_tokens:
                continue

            if token_clean in valid_units:
                unit_found = token.strip()
                continue

            cleaned_num = re.sub(r"[^\d\.]", "", token)
            if cleaned_num and cleaned_num != ".":
                try:
                    val = float(cleaned_num)
                    unit_candidate = re.sub(r"[\d\.]", "", token).strip()
                    numeric_tokens.append((val, unit_candidate))
                    if unit_candidate and unit_candidate.lower() in valid_units:
                        unit_found = unit_candidate
                    elif idx + 1 < len(tokens) and tokens[idx + 1].lower().strip() in valid_units:
                        unit_found = tokens[idx + 1].strip()
                except ValueError:
                    continue

        if not numeric_tokens:
            return {"value": None, "unit": None, "reference_range": ref_range}

        # Observed value is the primary numeric token in result column
        value = numeric_tokens[0][0]

        return {
            "value": round(value, 2),
            "unit": unit_found,
            "reference_range": ref_range,
        }
