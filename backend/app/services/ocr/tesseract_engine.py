"""
Tesseract OCR Engine implementation extending AbstractOCREngine.
Serves ONLY as an environment fallback when PaddleOCR cannot be initialized or executed.
"""

import os
import time
import logging
from typing import Union, List
import cv2
import numpy as np
import pytesseract
from PIL import Image

from app.services.ocr.base import AbstractOCREngine, OCRResult, OCRLine

logger = logging.getLogger(__name__)

# Tesseract executable lookup
_CANDIDATES = [
    os.getenv("TESSERACT_CMD"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]

_TESSERACT_CMD = None
for _path in _CANDIDATES:
    if _path and os.path.exists(_path):
        _TESSERACT_CMD = _path
        pytesseract.pytesseract.tesseract_cmd = _path
        break


class TesseractOCREngine(AbstractOCREngine):
    """
    Tesseract OCR Engine contract implementation for environment fallback.
    """

    @property
    def engine_name(self) -> str:
        return "Tesseract"

    def extract_text(self, image_input: Union[bytes, np.ndarray]) -> OCRResult:
        """
        Extract text using Tesseract PSM 6 mode as fallback.
        """
        start_time = time.time()
        logger.warning("[OCR] Engine used: Tesseract (ENVIRONMENT FALLBACK)")

        if isinstance(image_input, bytes):
            arr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes for Tesseract.")
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        pil_img = Image.fromarray(gray)
        config = "--oem 3 --psm 6 -l eng"

        try:
            data = pytesseract.image_to_data(pil_img, config=config, output_type=pytesseract.Output.DICT)
        except Exception as e:
            logger.error(f"[OCR] Tesseract execution failed: {e}")
            return OCRResult(
                engine_name="Tesseract",
                raw_text="",
                lines=[],
                ocr_confidence=0.0,
                is_fallback=True,
                processing_time_ms=round((time.time() - start_time) * 1000.0, 2),
                error_message=str(e),
            )

        ocr_lines: List[OCRLine] = []
        raw_text_parts: List[str] = []
        conf_scores: List[float] = []

        n_boxes = len(data["text"])
        line_buckets = {}  # group by top position line

        for i in range(n_boxes):
            txt = data["text"][i].strip()
            conf = float(data["conf"][i])
            if txt and conf > 0:
                top = data["top"][i]
                line_key = top // 15  # bucket nearby y-coordinates into lines
                if line_key not in line_buckets:
                    line_buckets[line_key] = []
                line_buckets[line_key].append((data["left"][i], txt, conf, data["width"][i], data["height"][i]))

        for l_key in sorted(line_buckets.keys()):
            words = sorted(line_buckets[l_key], key=lambda item: item[0])
            line_str = " ".join(w[1] for w in words)
            line_conf = sum(w[2] for w in words) / len(words)
            raw_text_parts.append(line_str)
            ocr_lines.append(OCRLine(text=line_str, confidence=line_conf / 100.0))
            conf_scores.append(line_conf)

        avg_conf = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0
        raw_text = "\n".join(raw_text_parts)
        elapsed_ms = (time.time() - start_time) * 1000.0

        return OCRResult(
            engine_name="Tesseract",
            raw_text=raw_text,
            lines=ocr_lines,
            ocr_confidence=round(avg_conf, 2),
            is_fallback=True,
            processing_time_ms=round(elapsed_ms, 2),
        )
