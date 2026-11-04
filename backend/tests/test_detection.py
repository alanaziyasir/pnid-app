import io
import uuid
from pathlib import Path

import cv2
import numpy as np
import pytest
from app import detector
from app.routers import detection
from PIL import Image

EXAMPLE = Path(__file__).resolve().parents[2] / "frontend/public/example.png"


@pytest.fixture(autouse=True)
def clear_template_cache():
    detector.load_templates.cache_clear()
    yield
    detector.load_templates.cache_clear()


def upload_image(client, image, name="diagram.png", image_format="PNG"):
    data = io.BytesIO()
    image.save(data, format=image_format)
    return client.post("/api/upload", files={"file": (name, data.getvalue())}).json()["file"]


def process(client, file):
    return client.post(
        "/api/detect",
        json={"stored_name": file["stored_name"]},
        headers={"X-Request-ID": "detection-regression"},
    )


def test_real_example_has_bounded_image_dependent_results(client):
    file = client.post("/api/upload", files={"file": ("example.png", EXAMPLE.read_bytes())}).json()[
        "file"
    ]
    response = process(client, file)
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "detection-regression"
    result = response.json()
    assert result["image_hw"] == [1500, 1500]
    assert result["detector"] == "template_matching"
    assert result["ocr_available"] is False
    assert result["limit_reached"] is False
    assert len(result["detections"]) >= 5
    for item in result["detections"]:
        assert 0 <= item["x1"] < item["x2"] <= 1500
        assert 0 <= item["y1"] < item["y2"] <= 1500
        assert detector.MATCH_THRESHOLD <= item["conf"] <= 1
        assert item["image_hw"] == [1500, 1500]
        assert "crop" not in item


@pytest.mark.parametrize("offset", [(31, 47), (150, 81)])
def test_translated_symbol_moves_detection_in_non_square_upload(client, offset):
    with Image.open(detector.TEMPLATE_DIR / "000_cls05_5.png") as template:
        image = Image.new("RGB", (320, 240), "white")
        image.paste(template, offset)
        width, height = template.size
    result = process(client, upload_image(client, image)).json()
    matches = [item for item in result["detections"] if item["class_id"] == 5]
    assert len(matches) == 1
    assert (matches[0]["x1"], matches[0]["y1"]) == offset
    assert (matches[0]["x2"], matches[0]["y2"]) == (offset[0] + width, offset[1] + height)
    assert matches[0]["image_hw"] == [240, 320]


def test_multiple_copies_survive_peak_suppression(client):
    image = Image.new("RGB", (400, 240), "white")
    with Image.open(detector.TEMPLATE_DIR / "000_cls05_5.png") as template:
        image.paste(template, (20, 30))
        image.paste(template, (220, 100))
    result = process(client, upload_image(client, image)).json()
    positions = {(item["x1"], item["y1"]) for item in result["detections"] if item["class_id"] == 5}
    assert positions == {(20, 30), (220, 100)}


@pytest.mark.parametrize("size", [(320, 240), (4, 3)])
def test_blank_uploads_return_no_components(client, size):
    result = process(client, upload_image(client, Image.new("RGB", size, "white"))).json()
    assert result["detections"] == []
    assert result["image_hw"] == [size[1], size[0]]


def test_transparent_image_is_flattened_and_jpeg_is_supported(client):
    transparent = upload_image(client, Image.new("RGBA", (100, 80), (0, 0, 0, 0)))
    jpeg = upload_image(client, Image.new("RGB", (120, 90)), "diagram.jpeg", "JPEG")
    assert process(client, transparent).json()["detections"] == []
    assert process(client, jpeg).json()["image_hw"] == [90, 120]


def test_small_nonconstant_image_has_no_large_template_matches(client):
    image = Image.new("RGB", (4, 3), "white")
    image.putpixel((0, 0), (0, 0, 0))
    assert process(client, upload_image(client, image)).json()["detections"] == []


@pytest.mark.parametrize(
    "name",
    [
        "../private.png",
        "/etc/passwd",
        "https://example.com/x.png",
        "%2e%2e%2fimage.png",
        "x\\y.png",
    ],
)
def test_rejects_arbitrary_paths_and_urls(client, name):
    assert client.post("/api/detect", json={"stored_name": name}).status_code == 400


def test_rejects_missing_and_unsupported_uploads(client):
    name = str(uuid.uuid4())
    assert client.post("/api/detect", json={"stored_name": f"{name}.png"}).status_code == 404
    assert client.post("/api/detect", json={"stored_name": f"{name}.pdf"}).status_code == 415
    assert client.post("/api/detect", json={}).status_code == 422


def test_symlink_cannot_escape_upload_storage(client, tmp_path):
    name = f"{uuid.uuid4()}.png"
    (tmp_path / name).symlink_to(EXAMPLE)
    response = client.post("/api/detect", json={"stored_name": name})
    assert response.status_code == 400
    assert str(EXAMPLE) not in response.text


@pytest.mark.parametrize("data", [b"not an image", b"\x89PNG\r\n\x1a\ntruncated"])
def test_corrupt_images_have_safe_errors(client, data):
    file = client.post("/api/upload", files={"file": ("private.png", data)}).json()["file"]
    response = process(client, file)
    assert response.status_code == 422
    assert response.json()["detail"] == "Unable to decode the uploaded image"
    assert "private.png" not in response.text


def test_disguised_non_raster_and_oversized_decoding_are_rejected(client):
    gif = upload_image(client, Image.new("RGB", (10, 10)), image_format="GIF")
    assert process(client, gif).status_code == 422
    large = upload_image(client, Image.new("L", (2001, 2000)))
    response = process(client, large)
    assert response.status_code == 422
    assert "4 million pixel" in response.json()["detail"]


def test_decompression_bomb_is_rejected(client, monkeypatch):
    file = upload_image(client, Image.new("RGB", (10, 10)))

    def bomb(*args, **kwargs):
        raise Image.DecompressionBombError("private path")

    monkeypatch.setattr(detector.Image, "open", bomb)
    assert process(client, file).status_code == 422


def test_missing_and_constant_templates_report_unavailable(client, tmp_path, monkeypatch):
    file = upload_image(client, Image.new("RGB", (100, 80)))
    monkeypatch.setattr(detector, "TEMPLATE_DIR", tmp_path)
    response = process(client, file)
    assert response.status_code == 503
    assert str(tmp_path) not in response.text
    Image.new("RGB", (20, 20)).save(tmp_path / detector.TEMPLATE_FILES[0][1])
    assert process(client, file).status_code == 503


def test_detector_failures_release_capacity(client, monkeypatch):
    file = upload_image(client, Image.new("RGB", (100, 80)))

    def fail(path):
        raise cv2.error("private detector internals")

    with monkeypatch.context() as patch:
        patch.setattr(detection, "detect", fail)
        response = process(client, file)
        assert response.status_code == 503
        assert "private" not in response.text
    assert process(client, file).status_code == 200
    assert detection.DETECTION_SLOTS.acquire(blocking=False)
    assert detection.DETECTION_SLOTS.acquire(blocking=False)
    try:
        assert process(client, file).status_code == 503
    finally:
        detection.DETECTION_SLOTS.release()
        detection.DETECTION_SLOTS.release()


def test_cross_template_duplicates_are_suppressed_and_results_are_capped(tmp_path, monkeypatch):
    path = tmp_path / "image.png"
    Image.fromarray(np.arange(100, dtype=np.uint8).reshape(10, 10)).save(path)
    match = detector.Detection(class_id=5, conf=1, x1=1, y1=1, x2=4, y2=4, image_hw=(10, 10))
    monkeypatch.setattr(detector, "template_matches", lambda *args: [match, match])
    assert len(detector.detect(path).detections) == 1
    monkeypatch.setattr(detector, "MAX_DETECTIONS", 1)
    assert detector.detect(path).limit_reached is True


def test_nonfinite_matching_scores_do_not_become_detections(monkeypatch):
    monkeypatch.setattr(cv2, "minMaxLoc", lambda scores: (0, float("nan"), (0, 0), (0, 0)))
    image = np.zeros((100, 100), dtype=np.uint8)
    assert detector.template_matches(image, 5, image[:10, :10]) == []
