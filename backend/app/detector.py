"""Bounded, fixed-scale template matching, not a trained P&ID model."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

MAX_IMAGE_PIXELS = 4_000_000
MAX_DETECTIONS = 100
MATCH_THRESHOLD = 0.94
TEMPLATE_DIR = Path(__file__).with_name("templates")
TEMPLATE_FILES = (
    (5, "000_cls05_5.png"),
    (2, "001_cls02_2.png"),
    (6, "002_cls06_6.png"),
    (14, "003_cls14_14.png"),
    (30, "004_cls30_30.png"),
    (17, "005_cls17_17.png"),
    (25, "006_cls25_25.png"),
    (6, "007_cls06_6.png"),
    (21, "008_cls21_21.png"),
    (11, "009_cls11_11.png"),
)
GrayImage = NDArray[np.uint8]


class InvalidImageError(ValueError):
    """The input cannot safely be processed as a supported raster."""


class DetectorUnavailableError(RuntimeError):
    """The local template library is missing or invalid."""


class Detection(BaseModel):
    class_id: int
    conf: float
    x1: int
    y1: int
    x2: int
    y2: int
    image_hw: tuple[int, int]


class DetectionResult(BaseModel):
    detector: Literal["template_matching"] = "template_matching"
    ocr_available: Literal[False] = False
    image_hw: tuple[int, int]
    detections: list[Detection]
    limit_reached: bool


def read_image(path: Path) -> GrayImage:
    """Check dimensions before decoding; flatten transparency onto white."""
    try:
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG"}:
                raise InvalidImageError("Detection supports PNG and JPEG images only")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise InvalidImageError("Image exceeds the 4 million pixel detection limit")
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            flattened = Image.alpha_composite(background, rgba).convert("L")
            return np.asarray(flattened, dtype=np.uint8)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise InvalidImageError("Image exceeds the safe decoding limit") from error
    except (OSError, UnidentifiedImageError, ValueError) as error:
        if isinstance(error, InvalidImageError):
            raise
        raise InvalidImageError("Unable to decode the uploaded image") from error


@lru_cache(maxsize=1)
def load_templates() -> tuple[tuple[int, GrayImage], ...]:
    templates = []
    try:
        for class_id, filename in TEMPLATE_FILES:
            template = read_image(TEMPLATE_DIR / filename)
            if float(template.std()) < 1:
                raise DetectorUnavailableError("Invalid template library")
            templates.append((class_id, template))
    except InvalidImageError as error:
        raise DetectorUnavailableError("Template library unavailable") from error
    return tuple(templates)


def template_matches(image: GrayImage, class_id: int, template: GrayImage) -> list[Detection]:
    height, width = image.shape
    template_height, template_width = template.shape
    if height < template_height or width < template_width:
        return []
    scores = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    matches = []
    for _ in range(MAX_DETECTIONS):
        _, score, _, (x, y) = cv2.minMaxLoc(scores)
        if not np.isfinite(score) or score < MATCH_THRESHOLD:
            break
        matches.append(
            Detection(
                class_id=class_id,
                conf=min(1.0, float(score)),
                x1=x,
                y1=y,
                x2=x + template_width,
                y2=y + template_height,
                image_hw=(height, width),
            )
        )
        # Suppress neighboring peaks, but keep separate copies of a symbol.
        scores[
            max(0, y - template_height // 2) : y + template_height // 2 + 1,
            max(0, x - template_width // 2) : x + template_width // 2 + 1,
        ] = -1
    return matches


def overlaps(first: Detection, second: Detection) -> bool:
    intersection = max(0, min(first.x2, second.x2) - max(first.x1, second.x1)) * max(
        0, min(first.y2, second.y2) - max(first.y1, second.y1)
    )
    union = (
        (first.x2 - first.x1) * (first.y2 - first.y1)
        + (second.x2 - second.x1) * (second.y2 - second.y1)
        - intersection
    )
    return intersection / union > 0.35


def detect(path: Path) -> DetectionResult:
    image = read_image(path)
    templates = load_templates()
    candidates = []
    # Constant images have no symbols and can produce undefined correlation.
    if float(image.std()) >= 1:
        for class_id, template in templates:
            candidates.extend(template_matches(image, class_id, template))
    detections: list[Detection] = []
    for candidate in sorted(candidates, key=lambda item: item.conf, reverse=True):
        if not any(overlaps(candidate, existing) for existing in detections):
            detections.append(candidate)
            if len(detections) == MAX_DETECTIONS:
                break
    return DetectionResult(
        image_hw=image.shape,
        detections=detections,
        limit_reached=len(detections) == MAX_DETECTIONS,
    )
