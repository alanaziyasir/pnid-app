"""
File upload endpoints
"""

import uuid
from pathlib import Path

import aiofiles
from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_DIR
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["upload"])


def validate_file(filename: str, file_size: int) -> None:
    """Validate file extension and size"""
    file_ext = Path(filename).suffix.lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file_ext}' not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024):.0f}MB",
        )


@router.post("/upload")
async def upload_file(file: UploadFile) -> JSONResponse:
    """
    Upload a P&ID diagram file

    Accepts: .pdf, .dwg, .dgn, .jpg, .png, .zip, .svg, .xml
    Max size: 50MB
    """
    file_path: Path | None = None
    try:
        filename = file.filename or ""
        validate_file(filename, 0)
        file_ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Bound memory use and reject over-limit streams before writing a chunk.
        file_size = 0
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                validate_file(filename, file_size)
                await f.write(chunk)

        # Return file info
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "File uploaded successfully",
                "file": {
                    "id": str(uuid.uuid4()),
                    "original_name": file.filename,
                    "stored_name": unique_filename,
                    "size": file_size,
                    "url": f"/uploads/{unique_filename}",
                    "type": file_ext,
                },
            },
        )

    except HTTPException:
        if file_path is not None:
            file_path.unlink(missing_ok=True)
        raise
    except OSError as error:
        if file_path is not None:
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to store uploaded file") from error
    finally:
        await file.close()


@router.get("/files")
async def list_files() -> dict[str, list[dict[str, str | int]]]:
    """List all uploaded files"""
    files: list[dict[str, str | int]] = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            files.append(
                {
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "url": f"/uploads/{file_path.name}",
                }
            )
    return {"files": files}
