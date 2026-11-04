"""Process an existing upload without accepting arbitrary paths or URLs."""

import re
from pathlib import Path
from threading import BoundedSemaphore

import cv2
from config import UPLOAD_DIR
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.detector import DetectionResult, DetectorUnavailableError, InvalidImageError, detect

router = APIRouter(prefix="/api", tags=["detection"])
DETECTION_SLOTS = BoundedSemaphore(2)
STORED_NAME = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\.[a-z0-9]{1,10}")


class DetectionRequest(BaseModel):
    stored_name: str = Field(min_length=1, max_length=64)


def upload_path(stored_name: str) -> Path:
    if not STORED_NAME.fullmatch(stored_name):
        raise HTTPException(status_code=400, detail="Invalid stored upload name")
    if Path(stored_name).suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=415, detail="Detection supports PNG and JPEG images only")
    path = UPLOAD_DIR / stored_name
    if path.is_symlink() or path.resolve().parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid stored upload path")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded image not found")
    return path


@router.post("/detect", response_model=DetectionResult)
def detect_upload(request: DetectionRequest) -> DetectionResult:
    """Match bundled templates at their original scale and orientation.

    Scores are normalized correlations, not calibrated probabilities. OCR is
    unavailable. PNG/JPEG decoding is limited to four million pixels.
    """
    path = upload_path(request.stored_name)
    if not DETECTION_SLOTS.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Detector is busy; please try again")
    try:
        return detect(path)
    except InvalidImageError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (DetectorUnavailableError, cv2.error) as error:
        raise HTTPException(status_code=503, detail="Detection is currently unavailable") from error
    finally:
        DETECTION_SLOTS.release()
