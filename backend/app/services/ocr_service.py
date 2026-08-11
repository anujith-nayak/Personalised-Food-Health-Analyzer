"""
OCR Service — Orchestrates image preprocessing, PaddleOCR primary engine, and fallback management.

Responsibilities:
  1. Calls table_cropper to crop ROI / assess image quality.
  2. Routes preprocessed image to PaddleOCREngine (primary engine).
  3. Uses TesseractOCREngine ONLY if PaddleOCR fails due to an installation/environment issue.
  4. Returns OCRResult (raw text, lines, bounding boxes, confidence, is_fallback flag).

Note: Nutrition parsing is kept strictly SEPARATE in app.services.ocr.nutrient_parser.
"""

import time
import logging
from typing import Tuple, Dict, Any, Optional

from app.services.ocr.base import OCRResult, AbstractOCREngine
from app.services.ocr.table_cropper import crop_and_enhance_table, assess_image_quality
from app.services.ocr.paddle_engine import PaddleOCREngine
from app.services.ocr.tesseract_engine import TesseractOCREngine

logger = logging.getLogger(__name__)

# Global singleton instances for primary and fallback engines
_PRIMARY_ENGINE: Optional[AbstractOCREngine] = None
_FALLBACK_ENGINE: Optional[AbstractOCREngine] = None

logger.info("[OCR] Primary engine registered: PaddleOCR")


def _get_primary_engine() -> AbstractOCREngine:
    global _PRIMARY_ENGINE
    if _PRIMARY_ENGINE is None:
        _PRIMARY_ENGINE = PaddleOCREngine()
    return _PRIMARY_ENGINE


def _get_fallback_engine() -> AbstractOCREngine:
    global _FALLBACK_ENGINE
    if _FALLBACK_ENGINE is None:
        _FALLBACK_ENGINE = TesseractOCREngine()
    return _FALLBACK_ENGINE


def extract_ocr_result(image_bytes: bytes) -> Tuple[OCRResult, Dict[str, Any]]:
    """
    Core OCR extraction function:
      1. Preprocesses image and extracts ROI table using OpenCV.
      2. Assesses image quality.
      3. Invokes primary PaddleOCR engine.
      4. If PaddleOCR experiences an environment/initialization error, falls back to Tesseract with is_fallback=True.
      5. Returns (OCRResult, cropper_metadata).
    """
    start_time = time.time()

    # Step 1: Preprocess and crop table ROI
    enhanced_img, cropper_meta = crop_and_enhance_table(image_bytes)
    quality = cropper_meta.get("quality", {})

    if not quality.get("is_usable", True):
        logger.warning(f"[OCR] Low image quality detected: {quality.get('summary')}")

    # Step 2: Run primary PaddleOCR engine
    primary = _get_primary_engine()
    try:
        ocr_result = primary.extract_text(enhanced_img)
        logger.info(f"[OCR] Primary engine (PaddleOCR) completed with confidence={ocr_result.ocr_confidence:.1f}%")
        return ocr_result, cropper_meta
    except Exception as paddle_err:
        logger.error(
            f"[OCR] Primary PaddleOCR engine failed due to environment/runtime error: {paddle_err}. "
            "Switching to Tesseract ENVIRONMENT FALLBACK.",
            exc_info=True,
        )
        # Step 3: Environment Fallback to Tesseract
        fallback = _get_fallback_engine()
        try:
            ocr_result = fallback.extract_text(enhanced_img)
            ocr_result.is_fallback = True
            ocr_result.error_message = f"PaddleOCR error: {paddle_err}"
            logger.warning("[OCR] Tesseract fallback extraction completed.")
            return ocr_result, cropper_meta
        except Exception as tess_err:
            logger.error(f"[OCR] Both primary and fallback OCR engines failed: {tess_err}")
            raise RuntimeError(f"OCR engines unavailable: PaddleOCR ({paddle_err}), Tesseract ({tess_err})") from tess_err


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Public API backward-compatibility wrapper function.
    Returns raw OCR string from OCRResult.
    """
    result, _ = extract_ocr_result(image_bytes)
    return result.raw_text
