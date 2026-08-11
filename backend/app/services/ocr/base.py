"""
Base classes and contracts for the modular OCR system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class OCRLine:
    text: str
    confidence: float
    bbox: Optional[List[Tuple[float, float]]] = None


@dataclass
class OCRResult:
    engine_name: str
    raw_text: str
    lines: List[OCRLine] = field(default_factory=list)
    ocr_confidence: float = 0.0
    is_fallback: bool = False
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


class AbstractOCREngine(ABC):
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Returns the name of the OCR engine."""
        pass

    @abstractmethod
    def extract_text(self, image_input) -> OCRResult:
        """Extract text and line details from image_bytes (bytes) or decoded numpy image (np.ndarray)."""
        pass

