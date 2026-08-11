"""
OpenCV ROI Cropper & Preprocessor for Nutrition Tables.

Isolates table bounding box, deskews, and applies contrast-enhancement
without applying destructive global binarization.
"""

import logging
from typing import Tuple, Dict, Any
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def assess_image_quality(img: np.ndarray) -> Dict[str, Any]:
    """
    Evaluates image quality metrics: resolution, blur (Laplacian variance),
    brightness, contrast (standard deviation).
    Returns a dict with metrics and usability recommendation.
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    h, w = gray.shape[:2]
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    # Thresholds for usability
    is_usable = True
    reasons = []

    if blur_score < 40.0:
        is_usable = False
        reasons.append(f"Image is too blurry (blur score {blur_score:.1f} < 40.0)")

    if brightness < 25.0:
        is_usable = False
        reasons.append(f"Image is too dark (brightness {brightness:.1f} < 25.0)")
    elif brightness > 245.0:
        is_usable = False
        reasons.append(f"Image is overexposed (brightness {brightness:.1f} > 245.0)")

    if contrast < 15.0:
        is_usable = False
        reasons.append(f"Image contrast is too low (contrast {contrast:.1f} < 15.0)")

    if min(w, h) < 150:
        is_usable = False
        reasons.append(f"Resolution too low ({w}x{h} px)")

    return {
        "is_usable": is_usable,
        "width": w,
        "height": h,
        "blur_score": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "reasons": reasons,
        "summary": "; ".join(reasons) if reasons else "Quality OK",
    }


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Applies perspective transform given 4 quad points."""
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped


def crop_and_enhance_table(image_bytes: bytes) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Decodes image_bytes, checks quality, detects table ROI (grid or borderless text block),
    applies optional perspective correction and CLAHE contrast enhancement.
    Returns (enhanced_image, metadata_dict).
    Guarantees safe fallback to full image if table ROI detection fails.
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes into OpenCV matrix.")

    quality = assess_image_quality(img)

    # Upscale if width is low
    h, w = img.shape[:2]
    min_w = 1200
    if w < min_w:
        scale = min_w / float(w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_area = h * w

    is_cropped = False
    perspective_applied = False
    table_box = None
    quad_contour = None

    # Strategy 1: Grid-line detection via morphological open
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 3
    )

    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))

    horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel)
    vert_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)
    table_mask = cv2.add(horiz_lines, vert_lines)

    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_area = 0

    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        area = bw * bh
        if 0.08 * img_area < area < 0.96 * img_area:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                quad_contour = approx.reshape(4, 2)

            if area > max_area:
                max_area = area
                table_box = (x, y, bw, bh)

    # Strategy 2: Borderless text-block density detection fallback
    if not table_box:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        morph_text = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        text_contours, _ = cv2.findContours(morph_text, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in text_contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            if 0.15 * img_area < area < 0.95 * img_area:
                if area > max_area:
                    max_area = area
                    table_box = (x, y, bw, bh)

    # Apply crop or perspective transformation if found
    if quad_contour is not None and max_area > 0.15 * img_area:
        try:
            cropped = _four_point_transform(img, quad_contour)
            gray_cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY) if len(cropped.shape) == 3 else cropped
            is_cropped = True
            perspective_applied = True
            logger.info("[CROPPER] Applied perspective correction on 4-point table quad")
        except Exception as e:
            logger.warning(f"[CROPPER] Perspective transform failed: {e}; fallback to bounding box")
            gray_cropped = gray

    elif table_box:
        x, y, bw, bh = table_box
        pad_x = int(bw * 0.03)
        pad_y = int(bh * 0.03)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w, x + bw + pad_x)
        y2 = min(h, y + bh + pad_y)

        gray_cropped = gray[y1:y2, x1:x2]
        is_cropped = True
        logger.info(f"[CROPPER] Isolated table ROI ({bw}x{bh} px)")
    else:
        gray_cropped = gray
        is_cropped = False
        logger.info("[CROPPER] No distinct table contour detected; using full image")

    # Apply CLAHE contrast enhancement + subtle sharpening (non-destructive)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_cropped)

    # Subtle sharpening
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    enhanced = cv2.addWeighted(enhanced, 1.3, blurred, -0.3, 0)

    # Convert to BGR format expected by PaddleOCR / OpenCV
    enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    metadata = {
        "quality": quality,
        "is_cropped": is_cropped,
        "perspective_applied": perspective_applied,
        "roi_dimensions": f"{gray_cropped.shape[1]}x{gray_cropped.shape[0]}" if is_cropped else f"{w}x{h}",
    }

    return enhanced_bgr, metadata

