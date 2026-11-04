from pathlib import Path

import pytest
from app.routers import upload
from fastapi import HTTPException


@pytest.mark.parametrize("name", ["diagram.PNG", "drawing.pdf", "x.jpeg", "x.dwg"])
def test_supported_extensions_and_size_boundary(name):
    upload.validate_file(name, upload.MAX_FILE_SIZE)


@pytest.mark.parametrize("name,size", [("x.exe", 1), ("", 0), ("x.png", 50 * 1024 * 1024 + 1)])
def test_rejects_invalid_files(name, size):
    with pytest.raises(HTTPException) as error:
        upload.validate_file(name, size)
    assert error.value.status_code == 400


@pytest.mark.integration
def test_upload_round_trip_and_safe_storage(client, tmp_path):
    data = b"\x89PNG\r\n\x1a\nexample"
    response = client.post("/api/upload", files={"file": ("../../diagram.png", data, "image/png")})
    assert response.status_code == 200
    info = response.json()["file"]
    assert info["size"] == len(data)
    assert Path(info["stored_name"]).name == info["stored_name"]
    assert (tmp_path / info["stored_name"]).read_bytes() == data
    fetched = client.get(info["url"])
    assert fetched.content == data
    assert fetched.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in fetched.headers["content-security-policy"]
    assert client.get("/api/files").json()["files"] == [
        {"name": info["stored_name"], "size": len(data), "url": info["url"]}
    ]


def test_rejected_upload_does_not_write_files(client, tmp_path):
    assert client.post("/api/upload", files={"file": ("bad.exe", b"no")}).status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_streaming_size_limit_cleans_partial_upload(client, tmp_path, monkeypatch):
    monkeypatch.setattr(upload, "MAX_FILE_SIZE", 1024 * 1024)
    response = client.post("/api/upload", files={"file": ("x.png", b"x" * (1024 * 1024 + 1))})
    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_storage_failure_does_not_expose_paths(client, tmp_path, monkeypatch):
    monkeypatch.setattr(upload, "UPLOAD_DIR", tmp_path / "missing")
    response = client.post("/api/upload", files={"file": ("x.png", b"data")})
    assert response.status_code == 500
    assert str(tmp_path) not in response.text


def test_list_ignores_directories(client, tmp_path):
    (tmp_path / "directory").mkdir()
    assert client.get("/api/files").json() == {"files": []}
