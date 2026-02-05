"""
Main FastAPI application for P&ID Digitization
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import upload, chat
from config import ALLOWED_ORIGINS, UPLOAD_DIR

app = FastAPI(
    title="P&ID Digitization API",
    description="Backend API for processing P&ID diagrams",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for serving files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include routers
app.include_router(upload.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {
        "message": "P&ID Digitization API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

