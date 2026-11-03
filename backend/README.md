# P&ID Digitization Backend

FastAPI provides upload/storage and chat endpoints. Follow
[QUICK_START.md](../QUICK_START.md) for complete installation, ports, environment
variables, credential-free local QA, and browser regression tests.

## Standalone development (Linux/macOS)

From the repository root:

```bash
python3 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements-deploy.txt
cd backend
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows use `venv\Scripts\python.exe`. For optional live chat, copy
`.env.example` to `.env`, set `GROQ_API_KEY`, and append `--env-file .env` to the
Uvicorn command. The app does not automatically load `.env`. Do not commit keys.
The default upload/preview workflow requires no credentials or database.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Health check |
| `POST /api/upload` | Multipart `file`, up to 50 MB |
| `GET /api/files` | List stored uploads |
| `GET /uploads/{stored_name}` | Retrieve a stored file |
| `GET /api/chat/models` | Available chat models |
| `GET /api/chat/graph-info` | Optional loaded graph context |
| `POST /api/chat/completions` | Chat via Groq (or the local QA provider) |
| `GET /docs` | Interactive Swagger UI |

Allowed extensions: `.pdf`, `.dwg`, `.dgn`, `.jpg`, `.jpeg`, `.png`, `.zip`,
`.svg`, `.xml`. Use PNG/JPEG for the browser image preview.

`requirements-deploy.txt` covers this API. The larger ML requirement files are
not needed for startup. There are no `/api/process/*` endpoints; the frontend
analysis currently displays sample data, not newly computed detections.
