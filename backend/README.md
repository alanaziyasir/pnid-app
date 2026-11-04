# P&ID Digitization Backend

Use Python 3.12. FastAPI provides upload/storage, detection, and chat endpoints. Follow
[QUICK_START.md](../QUICK_START.md) for complete installation, ports, environment
variables, credential-free local QA, and browser regression tests.

## Standalone development (Linux/macOS)

From the repository root:

```bash
python3 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements-deploy.txt
cd backend
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

On Windows use `venv\Scripts\python.exe`. For optional live chat, copy
`.env.example` to `.env`, set `GROQ_API_KEY`, and append `--env-file .env` to the
Uvicorn command. The app does not automatically load `.env`. Do not commit keys.
The default upload/preview workflow requires no credentials or database.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Health check |
| `GET /api/features` | Operational chat flag |
| `GET /metrics` | Prometheus metrics, only when ENABLE_METRICS=true |
| `POST /api/upload` | Multipart `file`, up to 50 MB |
| `POST /api/detect` | JSON `stored_name`; PNG/JPEG template matching, up to four million pixels |
| `GET /api/files` | List stored uploads |
| `GET /uploads/{stored_name}` | Retrieve a stored file |
| `GET /api/chat/models` | Available chat models |
| `GET /api/chat/graph-info` | Optional loaded graph context |
| `POST /api/chat/completions` | Chat via Groq (or the local QA provider) |
| `GET /docs` | Interactive Swagger UI |

Allowed extensions: `.pdf`, `.dwg`, `.dgn`, `.jpg`, `.jpeg`, `.png`, `.zip`,
`.svg`, `.xml`. Use PNG/JPEG for the browser image preview.

`requirements-deploy.txt` covers this API. The larger ML requirement files are
not needed for startup. The API includes Pillow, NumPy, headless OpenCV, and its
own bundled templates under `app/templates`; it does not need frontend files at
runtime. There are no `/api/process/*` endpoints.

Detection matches ten templates at their original scale and orientation, with
duplicate suppression, a 0.94 correlation threshold, and at most 100 results.
`conf` contains a correlation score, not a calibrated probability.
`image_hw` is `[height, width]`; `limit_reached` reports the result cap.
`ocr_available` is always false. No OCR, model download, CAD/PDF conversion,
image-to-graph conversion, or per-upload chat graph is implemented.

Only upload-generated basenames are accepted. Missing uploads return 404,
unsupported extensions 415, invalid image content/dimensions 422, and unavailable
or busy detection 503. Up to two requests run concurrently in the server thread
pool rather than blocking the async event loop.
