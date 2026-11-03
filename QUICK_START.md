# Run and interactively QA P&ID Digitization

The application consists of a Next.js frontend and a FastAPI backend. Neither
has a login gate. Upload and preview need no external services. Live chat needs
a Groq API key; the local QA path below replaces only that external provider
with a clearly labeled HTTP stub. It runs the real frontend and backend.

## 1. Install dependencies (Linux/macOS)

Requirements: Python 3.10+ with `venv`/pip, Node.js 20.9+ (22 or 24 recommended),
and npm. Run these commands from the repository root:

```bash
# Create the venv if backend/venv does not already exist.
python3 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements-deploy.txt
npm --prefix frontend ci
```

`requirements-deploy.txt` contains everything imported by the running API,
including `httpx`. The larger `requirements.txt` and `requirements_minimal.txt`
are for experimental image/ML tools, not required to run this application.
No database, GPU, model download, GraphML file, or API credentials are needed
for local QA.

On Windows, create the venv with `python -m venv backend/venv` and use
`backend\venv\Scripts\python.exe` in place of `backend/venv/bin/python`.
Use `python` in place of `python3` when launching the QA script.

## 2. Launch both applications

From the repository root:

```bash
python3 scripts/run_qa.py
```

Wait for `QA ready`, then open **http://127.0.0.1:3000**.
The API is at **http://127.0.0.1:8000**, its health endpoint is `/health`,
and interactive API docs are at `/docs`.

The launcher binds only to loopback, sets the frontend API URL and backend CORS
origin together, and starts an in-process provider stub on an available
loopback port. It overrides inherited Groq credentials/URL with a QA-only token
and stub URL, so chat never contacts Groq. Uploaded files live in a new temporary
directory, not `backend/uploads`. Ctrl+C (or SIGTERM) stops both child servers,
closes the stub, and removes only that run's temporary uploads.

If a port is occupied, the launcher fails instead of reusing or killing another
server. Choose two free ports:

```bash
python3 scripts/run_qa.py --frontend-port 3001 --backend-port 8001
```

Open the printed frontend URL. Always use that exact origin; `localhost` and
`127.0.0.1` are different CORS origins on custom ports.

## 3. Drive a meaningful end-to-end interaction

1. Choose **Upload Your Diagram**, then select the bundled
   `frontend/public/example.png` (1500 × 1500). The maximum upload size is 50 MB.
2. Confirm `example.png`, **Uploaded**, and a visible image preview.
3. Use **Expand diagram** to view fullscreen, then **Close fullscreen**.
4. Click **Process**. Confirm navigation to `/analysis?file=...`, the same image,
   a **Summary**, and 10 sample components.
5. Click **Tags**, **Components**, and **All**. Confirm the overlay boxes change.
6. Enter `Which components are connected?` and send it. Expect:
   `[Local QA stub, no AI inference] Received: Which components are connected?`
7. Return to the home page, upload again, and use **Remove diagram** to confirm
   the upload picker returns.

The analysis page currently uses bundled sample detections, OCR, and crop
images for every upload. **Process does not perform new OCR/preprocessing**;
there are no `/api/process/*` routes. The stub verifies the provider request
shape and echoes the question; it does not validate model quality or graph
reasoning. Those limitations are not hidden by this QA workflow.

## Automated browser regression

After dependency setup, run from the repository root:

```bash
cd frontend
npx playwright install chromium
# On a Linux image missing browser libraries, use (may require sudo):
# npx playwright install --with-deps chromium
npm run test:e2e
npm run type-check
```

Launcher/provider safety tests (from the repository root, after setup):

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
```

Playwright starts and stops its own isolated stack on **3100/8100**, with no
reuse of existing servers. It checks upload over HTTP, exact stored image bytes,
loaded previews, fullscreen, navigation, overlay tabs, chat through the backend
and local provider, removal, and unsupported-file rejection. Ports 3100/8100
must be free. Failures retain traces under `frontend/test-results/`.

Next.js owns `frontend/next-env.d.ts` and `.next/`; both are generated and ignored.
Startup and `npm run type-check` generate the types without changing tracked
files. Do not restore or hand-edit `next-env.d.ts`. Type-check runs
`next typegen` first, so it also works on a clean checkout.

## Normal development and optional live chat

For development without the stub, start each server in its own terminal:

```bash
# Terminal 1, from the repository root
cd backend
# Optional: copy .env.example to .env and set GROQ_API_KEY for live chat.
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# If using .env, append: --env-file .env
```

```bash
# Terminal 2, from the repository root
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

The frontend defaults to `http://localhost:8000`. For custom ports or a browser
on a different host, copy `frontend/.env.example` to `frontend/.env.local` and set
`NEXT_PUBLIC_API_URL` to a URL **reachable by the browser**, not a container-only
hostname. Restart Next.js after changing it (rebuild for production).

| Setting | Used by | Default / purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Frontend | `http://localhost:8000`; uploads, image URLs, chat |
| `FRONTEND_URL` | Backend | Extra exact allowed CORS origin; localhost and 127.0.0.1 on port 3000 are already allowed |
| `GROQ_API_KEY` | Backend only | Unset; required only for live chat, never put in a `NEXT_PUBLIC_*` variable |
| `GROQ_API_URL` | Backend only | Groq's chat completions endpoint; overridden by the QA launcher |
| `GRAPHML_PATH` | Backend only | `data/graph.graphml`, relative to the backend working directory; optional live chat context |
| `UPLOAD_DIR` | Backend only | `backend/uploads`; QA overrides this with temporary storage |

There is no automatic `.env` loading in the backend: export variables before
startup or pass `--env-file .env` to Uvicorn. Missing graph data logs a warning
and leaves chat without graph context. Without a key, live chat returns an error;
uploads/preview still work. Use the local QA launcher for credential-free chat.

## Troubleshooting

- **Upload fails / CORS:** check the backend URL and exact frontend origin above.
  `NEXT_PUBLIC_API_URL` is read by browser code, not just the Next.js server.
- **Backend import errors:** install `requirements-deploy.txt` with the venv's
  Python, and run Uvicorn from `backend`, not from the repository root.
- **Missing venv/Next.js:** complete step 1; the launcher explains missing tools.
- **Port in use:** select other ports rather than stopping unrelated processes.
- **Browser unavailable in a restricted environment:** run the launcher, check
  `/health` and `/api/chat/models` in `/docs`, upload the bundled image via
  `POST /api/upload`, and retrieve its returned `/uploads/...` URL. This checks
  the API only; it does not replace the browser interaction above.
