"""
OCR Service — Multi-preprocessing + keyword-scored best result.

Strategy:
  1. Generate 6 preprocessed versions of the image
  2. Run Tesseract on each with PSM modes 3, 4, 6, 11, 12
  3. Score every result by counting nutrition keywords found
  4. Return the result with the HIGHEST keyword score (not longest text)
  5. Warn if fewer than 5 keywords found

Only this file is modified. Nutrition parser is untouched.
"""
import os
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# ── Tesseract path ────────────────────────────────────────────────────────────
_CANDIDATES = [
    os.getenv("TESSERACT_CMD", ""),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]
for _path in _CANDIDATES:
    if _path and os.path.exists(_path):
        pytesseract.pytesseract.tesseract_cmd = _path
        logger.info(f"[OCR] Tesseract: {_path}")
        break

# ── Nutrition keywords for scoring ───────────────────────────────────────────
NUTRITION_KEYWORDS = [
    "calories", "total fat", "saturated fat", "trans fat",
    "cholesterol", "sodium", "carbohydrate", "fiber", "sugar", "protein",
    "total sugars", "dietary fiber", "serving size", "amount per",
]

def _keyword_score(text: str) -> int:
    """Count how many nutrition keywords appear in the OCR text."""
    t = text.lower()
    return sum(1 for kw in NUTRITION_KEYWORDS if kw in t)


# ── Image preprocessing variants ─────────────────────────────────────────────

def _preprocess_variants(image_bytes: bytes) -> list[tuple[str, np.ndarray]]:
    """
    Return a list of (name, preprocessed_image) pairs.
    Each variant targets a different OCR challenge (blur, low contrast, etc).
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    orig = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if orig is None:
        raise ValueError("Could not decode image. Ensure it is a valid JPG or PNG.")

    # Upscale small images for better OCR
    h, w = orig.shape[:2]
    if w < 1000:
        scale = 1400 / w
        orig = cv2.resize(orig, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)

    variants: list[tuple[str, np.ndarray]] = []

    # 1. Grayscale — fastest, good baseline
    variants.append(("grayscale", gray))

    # 2. Otsu threshold — best for clean white-background nutrition labels
    denoised = cv2.fastNlMeansDenoising(gray, h=8)
    _, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu_threshold", otsu))

    # 3. Adaptive threshold — handles uneven lighting and shadows
    adaptive = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 15, 4
    )
    variants.append(("adaptive_threshold", adaptive))

    return variants


# ── Single OCR run ────────────────────────────────────────────────────────────

def _run_tesseract(image: np.ndarray, psm: int) -> str:
    """Run Tesseract on one image with one PSM mode. Returns text."""
    pil = Image.fromarray(image)
    config = f"--oem 3 --psm {psm} -l eng"
    try:
        return pytesseract.image_to_string(pil, config=config)
    except Exception as e:
        logger.warning(f"  Tesseract error psm={psm}: {e}")
        return ""


# ── Main extraction function ──────────────────────────────────────────────────

PSM_MODES = [6, 4]   # 6=uniform block (best for labels), 4=single column

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Fast multi-pass OCR: 3 variants × 2 PSM modes = 6 attempts max.
    Early exit when score ≥ 8 keywords found.
    Typical time: 2-4 seconds.
    """
    all_variants = _preprocess_variants(image_bytes)

    # Best 3 variants for nutrition labels
    fast_variants = [v for v in all_variants if v[0] in (
        "grayscale", "otsu_threshold", "adaptive_threshold"
    )]
    if not fast_variants:
        fast_variants = all_variants[:3]

    best_text  = ""
    best_score = -1
    best_label = ""

    logger.info("OCR: %d variants × %d PSM = %d attempts max",
                len(fast_variants), len(PSM_MODES), len(fast_variants) * len(PSM_MODES))

    for variant_name, img in fast_variants:
        for psm in PSM_MODES:
            text  = _run_tesseract(img, psm)
            score = _keyword_score(text)
            label = f"{variant_name} PSM={psm}"

            logger.info(f"  {label:35} keywords={score:2d}  chars={len(text):4d}")
            if score > 0:
                found_kw = [kw for kw in NUTRITION_KEYWORDS if kw in text.lower()]
                logger.info(f"    found: {found_kw}")

            if score > best_score or (score == best_score and len(text) > len(best_text)):
                best_score = score
                best_text  = text
                best_label = label

            # Early exit — stop as soon as we have a good result
            if best_score >= 8:
                logger.info(f"  Early exit at score {best_score}")
                break

        if best_score >= 8:
            break
            break

    logger.info("=" * 70)
    logger.info(f"BEST RESULT: {best_label}  keyword_score={best_score}")
    logger.info("===== RAW OCR TEXT (best) =====")
    logger.info(best_text[:800])
    logger.info("=" * 70)

    # Warn if too few nutrition fields found
    if best_score < 4:
        logger.warning(
            "OCR extracted fewer than 4 nutrition keywords. "
            "Image may be blurry or label not fully visible."
        )
        # Still return what we have — the route will check nutrition_facts emptiness
        if best_score == 0:
            raise ValueError(
                "Unable to read nutrition facts from this image. "
                "Please retake the photo with the Nutrition Facts panel "
                "fully visible and well-lit."
            )

    return best_text
