"""
PaddleOCR Engine implementation extending AbstractOCREngine.
Uses PaddleOCR as the primary engine for high-accuracy nutrition label text & spatial extraction.
"""

import os
import time
import logging
from typing import Union, List, Tuple
import cv2
import numpy as np

from app.services.ocr.base import AbstractOCREngine, OCRResult, OCRLine

logger = logging.getLogger(__name__)


class PaddleOCREngine(AbstractOCREngine):
    """
    PaddleOCR Engine implementing AbstractOCREngine contract.
    Lazy initializes PaddleOCR instance on first call.
    """

    def __init__(self, lang: str = "en", use_angle_cls: bool = True):
        self._lang = lang
        self._use_angle_cls = use_angle_cls
        self._ocr = None
        self._init_error = None

    @property
    def engine_name(self) -> str:
        return "PaddleOCR"

    def _get_ocr_instance(self):
        if self._ocr is not None:
            return self._ocr

        if self._init_error is not None:
            raise RuntimeError(f"PaddleOCR failed initialization previously: {self._init_error}")

        try:
            logger.info("[OCR] Initializing primary engine: PaddleOCR...")
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            os.environ["FLAGS_use_mkldnn"] = "0"
            os.environ["FLAGS_enable_pir_api"] = "0"
            import paddle
            if hasattr(paddle, "disable_signal_handler"):
                paddle.disable_signal_handler()
            from paddleocr import PaddleOCR
            # Initialize PaddleOCR with CPU flags
            self._ocr = PaddleOCR(use_textline_orientation=True, enable_mkldnn=False, lang=self._lang)
            logger.info("[OCR] Primary engine: PaddleOCR successfully initialized.")
            return self._ocr
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"[OCR] Failed to initialize PaddleOCR engine: {e}", exc_info=True)
            raise RuntimeError(f"PaddleOCR initialization failed: {e}") from e

    def extract_text(self, image_input: Union[bytes, np.ndarray]) -> OCRResult:
        """
        Extract text, line bounding boxes, and line confidence scores using PaddleOCR.
        """
        start_time = time.time()
        logger.info("[OCR] Engine used: PaddleOCR")

        # Decode image if bytes
        if isinstance(image_input, bytes):
            arr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes for PaddleOCR.")
        elif isinstance(image_input, np.ndarray):
            img = image_input
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        try:
            ocr_instance = self._get_ocr_instance()
            if hasattr(ocr_instance, "predict"):
                results = ocr_instance.predict(img)
            else:
                results = ocr_instance.ocr(img)
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.error(f"[OCR] PaddleOCR execution error: {e}")
            raise RuntimeError(f"PaddleOCR execution failed: {e}") from e

        ocr_lines: List[OCRLine] = []
        raw_text_parts: List[str] = []
        total_confidence = 0.0

        if results and len(results) > 0:
            res_item = results[0]
            if isinstance(res_item, dict):
                rec_texts = res_item.get("rec_texts", [])
                rec_scores = res_item.get("rec_scores", [])
                dt_polys = res_item.get("dt_polys", [])

                for idx, text in enumerate(rec_texts):
                    conf = float(rec_scores[idx]) if idx < len(rec_scores) else 0.0
                    poly = dt_polys[idx] if idx < len(dt_polys) else None
                    if poly is not None and hasattr(poly, "tolist"):
                        poly = poly.tolist()
                    bbox_tuples = [(float(pt[0]), float(pt[1])) for pt in poly] if poly else None

                    ocr_lines.append(OCRLine(text=text, confidence=conf, bbox=bbox_tuples))
                    raw_text_parts.append(text)
                    total_confidence += conf
            elif isinstance(res_item, list):
                for line in res_item:
                    if not line or len(line) < 2:
                        continue
                    bbox_coords = line[0]
                    text_score = line[1]
                    if isinstance(text_score, (tuple, list)):
                        text, conf = text_score[0], float(text_score[1])
                    else:
                        text, conf = str(text_score), 0.0

                    bbox_tuples = [(float(pt[0]), float(pt[1])) for pt in bbox_coords] if bbox_coords else None
                    ocr_lines.append(OCRLine(text=text, confidence=conf, bbox=bbox_tuples))
                    raw_text_parts.append(text)
                    total_confidence += conf

        avg_conf = (total_confidence / len(ocr_lines)) * 100.0 if ocr_lines else 0.0
        raw_text = "\n".join(raw_text_parts)
        elapsed_ms = (time.time() - start_time) * 1000.0

        logger.info(f"[OCR] PaddleOCR extracted {len(ocr_lines)} lines with confidence={avg_conf:.1f}% ({elapsed_ms:.0f}ms)")

        return OCRResult(
            engine_name="PaddleOCR",
            raw_text=raw_text,
            lines=ocr_lines,
            ocr_confidence=round(avg_conf, 2),
            is_fallback=False,
            processing_time_ms=round(elapsed_ms, 2),
        )
