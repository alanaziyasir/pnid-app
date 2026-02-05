"""
File upload endpoints
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import aiofiles
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE

router = APIRouter(prefix="/api", tags=["upload"])

def validate_file(filename: str, file_size: int) -> None:
    """Validate file extension and size"""
    file_ext = Path(filename).suffix.lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file_ext}' not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.0f}MB"
        )

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a P&ID diagram file
    
    Accepts: .pdf, .dwg, .dgn, .jpg, .png, .zip, .svg, .xml
    Max size: 50MB
    """
    try:
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        
        # Validate file
        validate_file(file.filename, file_size)
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
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
                    "type": file_ext
                }
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/files")
async def list_files():
    """List all uploaded files"""
    files = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "url": f"/uploads/{file_path.name}"
            })
    return {"files": files}

