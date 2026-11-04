"""
Main FastAPI application for P&ID Digitization
"""

from config import ALLOWED_ORIGINS, ENABLE_CHAT, ENABLE_METRICS, SENTRY_DSN, UPLOAD_DIR
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.observability import RequestTelemetry, init_error_tracking
from app.routers import chat, detection, events, upload

init_error_tracking(SENTRY_DSN)

app = FastAPI(
    title="P&ID Digitization API",
    description="Backend API for processing P&ID diagrams",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials="*" not in ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestTelemetry)

# Mount uploads directory for serving files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include routers
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(detection.router)
app.include_router(events.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "P&ID Digitization API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/features")
async def features() -> dict[str, bool]:
    return {"chat": ENABLE_CHAT}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not ENABLE_METRICS:
        return Response(status_code=404)
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})
