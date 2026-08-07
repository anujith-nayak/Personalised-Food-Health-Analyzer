"""
OCR Service — Robust multi-preprocessing pipeline for nutrition labels.

Strategy:
  1. Aggressively preprocess the image with multiple variants:
       grayscale, denoised, sharpened, CLAHE, Otsu, adaptive threshold,
       deskewed, inverted, morphologically cleaned.
  2. Run Tesseract with multiple PSM modes (3, 4, 6, 11, 12) on each variant.
  3. Score every result by counting nutrition keywords found.
  4. Return the highest-scoring result (ties broken by character count).
  5. Log every attempt, matched keywords, and warn on low scores.
"""

import os
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# ── Tesseract path ─────────────────────────────────────────────────────────────
_CANDIDATES = [
    os.getenv("TESSERACT_CMD"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]

_TESSERACT_FOUND = False
for _path in _CANDIDATES:
    if _path and os.path.exists(_path):
        pytesseract.pytesseract.tesseract_cmd = _path
        logger.info(f"[OCR] Using Tesseract: {_path}")
        _TESSERACT_FOUND = True
        break

if not _TESSERACT_FOUND:
    logger.error("[OCR] Tesseract executable NOT FOUND in any known location!")

# ── Nutrition keywords for scoring ────────────────────────────────────────────
# The more of these appear in OCR output, the better the result quality.
NUTRITION_KEYWORDS = [
    "calories", "energy", "kcal", "kj",
    "protein",
    "total fat", "fat",
    "saturated fat", "saturated",
    "trans fat", "trans",
    "cholesterol",
    "sodium", "salt",
    "total carbohydrate", "carbohydrate", "carbohydrates", "carbs",
    "dietary fiber", "dietary fibre", "fiber", "fibre",
    "total sugars", "sugar", "sugars",
    "added sugar", "added sugars",
    "potassium",
    "calcium",
    "iron",
    "vitamin",
    "serving size", "serving",
    "amount per", "daily value",
    "nutrition facts", "nutritional information",
]

# Nutrients we specifically care about — used for missed-nutrient logging
TARGET_NUTRIENTS = [
    "calories", "total fat", "saturated fat", "trans fat", "cholesterol",
    "sodium", "carbohydrate", "fiber", "sugar", "protein",
    "potassium", "calcium", "iron",
]


def _keyword_score(text: str) -> int:
    """Count how many nutrition keywords appear in the OCR text (case-insensitive)."""
    t = text.lower()
    return sum(1 for kw in NUTRITION_KEYWORDS if kw in t)


def _missed_nutrients(text: str) -> list[str]:
    """Return list of target nutrients NOT found in the OCR text."""
    t = text.lower()
    return [n for n in TARGET_NUTRIENTS if n not in t]


# ── Image preprocessing pipeline ──────────────────────────────────────────────

def _upscale_if_needed(img: np.ndarray, min_width: int = 1200) -> np.ndarray:
    """Upscale image so OCR has enough pixel density to work with."""
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    return img


def _deskew(img: np.ndarray) -> np.ndarray:
    """Rotate image to correct minor tilt (±15 degrees)."""
    coords = np.column_stack(np.where(img < 128))
    if len(coords) < 50:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5 or abs(angle) > 15:
        return img
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    return rotated


def _apply_clahe(gray: np.ndarray) -> np.ndarray:
    """Apply CLAHE to boost local contrast — helps faint text on light backgrounds."""
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _sharpen(gray: np.ndarray) -> np.ndarray:
    """Unsharp mask sharpening — more controlled than a raw Laplacian kernel."""
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    sharpened = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    return sharpened


def _morph_clean(binary: np.ndarray) -> np.ndarray:
    """
    Morphological opening to remove isolated noise pixels,
    followed by closing to reconnect broken character strokes.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel2, iterations=1)
    return cleaned


def _preprocess_variants(image_bytes: bytes) -> list[tuple[str, np.ndarray]]:
    """
    Generate multiple preprocessed versions of the nutrition label image.
    Returns list of (name, image_array) pairs for Tesseract to try.

    Variants produced:
      1. grayscale_upscaled   — baseline, fast
      2. denoised             — removes camera/scan noise
      3. sharpened            — enhances text edges
      4. clahe                — improves low-contrast labels
      5. otsu                 — clean binarisation for crisp labels
      6. adaptive_gaussian    — handles shadows / uneven lighting
      7. adaptive_mean        — alternative adaptive method
      8. deskewed_otsu        — corrects tilted images then binarises
      9. inverted_otsu        — for dark-background / inverted labels
     10. morph_cleaned        — removes noise from binary image
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    orig = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if orig is None:
        raise ValueError("Could not decode image. Ensure it is a valid JPG or PNG.")

    orig = _upscale_if_needed(orig)
    gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)

    variants: list[tuple[str, np.ndarray]] = []

    # 1. Plain grayscale
    variants.append(("grayscale", gray))

    # 2. Denoised grayscale
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    variants.append(("denoised", denoised))

    # 3. Sharpened
    sharpened = _sharpen(denoised)
    variants.append(("sharpened", sharpened))

    # 4. CLAHE (contrast-limited adaptive histogram equalisation)
    clahe_img = _apply_clahe(denoised)
    variants.append(("clahe", clahe_img))

    # 5. Otsu threshold on denoised
    _, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu", otsu))

    # 6. Adaptive Gaussian threshold — best for uneven lighting
    adaptive_gauss = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 13, 3
    )
    variants.append(("adaptive_gaussian", adaptive_gauss))

    # 7. Adaptive Mean threshold
    adaptive_mean = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY, 13, 4
    )
    variants.append(("adaptive_mean", adaptive_mean))

    # 8. Deskewed + Otsu — corrects camera tilt
    deskewed = _deskew(otsu)
    variants.append(("deskewed_otsu", deskewed))

    # 9. Inverted Otsu — for labels with dark backgrounds
    _, otsu_inv = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    variants.append(("inverted_otsu", otsu_inv))

    # 10. Morphologically cleaned binary
    morph = _morph_clean(otsu)
    variants.append(("morph_cleaned", morph))

    return variants


# ── Tesseract runner ───────────────────────────────────────────────────────────

PSM_MODES = [6, 4, 3, 11, 12]
# PSM 6  — assume uniform block of text (best for most nutrition labels)
# PSM 4  — assume single column of text (good for tall narrow labels)
# PSM 3  — fully automatic (default Tesseract heuristic)
# PSM 11 — sparse text, no particular order (catches scattered layout)
# PSM 12 — sparse text with OSD

def _run_tesseract(image: np.ndarray, psm: int, variant_name: str) -> str:
    """Run Tesseract on one (variant, PSM) pair. Returns raw OCR string."""
    pil_img = Image.fromarray(image)
    config = f"--oem 3 --psm {psm} -l eng"
    try:
        text = pytesseract.image_to_string(pil_img, config=config)
        logger.debug(f"  [{variant_name}|PSM{psm}] chars={len(text.strip())}")
        return text
    except Exception:
        logger.exception(f"  [{variant_name}|PSM{psm}] Tesseract raised an exception")
        return ""


# ── Main public function ───────────────────────────────────────────────────────

# Fast variant set — tried first; full set used only if score stays low
_FAST_VARIANTS = {"grayscale", "otsu", "adaptive_gaussian", "sharpened", "clahe"}
_EARLY_EXIT_SCORE = 9    # stop trying if we already found this many keywords
_FULL_SET_THRESHOLD = 5  # if fast variants score below this, try all variants


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Multi-preprocessing + multi-PSM OCR pipeline.

    1. Generates up to 10 preprocessing variants.
    2. Tries PSM modes 6, 4, 3 on the fast variant subset first.
    3. Exits early if keyword score ≥ 9.
    4. If score is still below threshold, tries remaining variants + more PSM modes.
    5. Logs: raw OCR text, keyword score, matched keywords, missed nutrients.
    6. Returns the best OCR text for the downstream nutrition parser.
    """
    logger.info("=" * 70)
    logger.info("[OCR] Starting extraction pipeline")

    all_variants = _preprocess_variants(image_bytes)

    best_text  = ""
    best_score = -1
    best_label = ""

    # ── Phase 1: fast variants, PSM 6 + 4 ────────────────────────────────────
    fast = [(n, img) for n, img in all_variants if n in _FAST_VARIANTS]
    logger.info(f"[OCR] Phase 1: {len(fast)} fast variants × [6,4,3] PSM")

    for v_name, img in fast:
        for psm in [6, 4, 3]:
            text  = _run_tesseract(img, psm, v_name)
            score = _keyword_score(text)
            label = f"{v_name}|PSM{psm}"

            _log_attempt(label, text, score)

            if score > best_score or (score == best_score and len(text) > len(best_text)):
                best_score = score
                best_text  = text
                best_label = label

            if best_score >= _EARLY_EXIT_SCORE:
                logger.info(f"[OCR] Early exit — score {best_score} after {label}")
                break
        if best_score >= _EARLY_EXIT_SCORE:
            break

    # ── Phase 2: full variant set + remaining PSM modes ───────────────────────
    if best_score < _FULL_SET_THRESHOLD:
        slow = [(n, img) for n, img in all_variants if n not in _FAST_VARIANTS]
        logger.info(f"[OCR] Phase 2 triggered (score={best_score}): "
                    f"{len(slow)} more variants × all PSM modes")

        for v_name, img in slow:
            for psm in PSM_MODES:
                text  = _run_tesseract(img, psm, v_name)
                score = _keyword_score(text)
                label = f"{v_name}|PSM{psm}"

                _log_attempt(label, text, score)

                if score > best_score or (score == best_score and len(text) > len(best_text)):
                    best_score = score
                    best_text  = text
                    best_label = label

                if best_score >= _EARLY_EXIT_SCORE:
                    logger.info(f"[OCR] Phase-2 early exit — score {best_score}")
                    break
            if best_score >= _EARLY_EXIT_SCORE:
                break

    # ── Summary log ───────────────────────────────────────────────────────────
    logger.info("=" * 70)
    logger.info(f"[OCR] BEST: {best_label}  keyword_score={best_score}")

    matched  = [kw for kw in NUTRITION_KEYWORDS if kw in best_text.lower()]
    missed   = _missed_nutrients(best_text)
    confidence = min(100, int(best_score / len(NUTRITION_KEYWORDS) * 200))

    logger.info(f"[OCR] Matched keywords ({len(matched)}): {matched}")
    logger.info(f"[OCR] Missed target nutrients ({len(missed)}): {missed}")
    logger.info(f"[OCR] Extraction confidence estimate: ~{confidence}%")
    logger.info("── Best OCR text (first 1000 chars) ──")
    logger.info(best_text[:1000])
    logger.info("=" * 70)

    if best_score < 3:
        logger.warning(
            "[OCR] Keyword score < 3. Image may be blurry, heavily skewed, "
            "or the nutrition panel is not visible."
        )

    return best_text


def _log_attempt(label: str, text: str, score: int) -> None:
    """Structured log for one OCR attempt."""
    found_kw = [kw for kw in NUTRITION_KEYWORDS if kw in text.lower()]
    logger.info(f"  {label:35}  score={score:2d}  chars={len(text.strip()):4d}  "
                f"found={found_kw[:5]}")
