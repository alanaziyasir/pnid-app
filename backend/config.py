"""
Configuration settings for the P&ID Digitization backend
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Upload settings
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".dwg", ".dgn", ".jpg", ".jpeg", ".png", ".zip", ".svg", ".xml"}

# Max file size (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Operational kill switch, not an authorization boundary.
ENABLE_CHAT = os.getenv("ENABLE_CHAT", "true").lower() == "true"
# Scrape only on a trusted network; the endpoint is disabled by default.
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "false").lower() == "true"
# Optional Sentry DSN; empty leaves error tracking fully disabled.
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add production origins from environment
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

# Allow all origins in production if specified
if os.getenv("ALLOW_ALL_ORIGINS", "").lower() == "true":
    ALLOWED_ORIGINS = ["*"]
