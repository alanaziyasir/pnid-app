# P&ID Digitization setup

Use [QUICK_START.md](QUICK_START.md) for current setup and interactive QA.
Servers are not assumed to be running.

- `frontend/`: Next.js 15 and React 18 upload/preview and sample analysis UI.
- `backend/`: FastAPI upload/storage and Groq chat API.
- `scripts/run_qa.py`: isolated local stack with a credential-free chat stub.
- `frontend/e2e/`: browser regression tests against both real applications.

The analysis UI uses sample detections/OCR. Upload storage and chat integration
are implemented; new OCR/preprocessing and database integration are not part of
the running API. See the quick start for these limitations and live-chat setup.
