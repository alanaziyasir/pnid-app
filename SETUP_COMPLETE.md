# P&ID Digitization setup

Use [QUICK_START.md](QUICK_START.md) for current setup and interactive QA.
Servers are not assumed to be running.

- `frontend/`: Next.js 15 and React 18 upload/preview and detection analysis UI.
- `backend/`: FastAPI upload/storage, local template detection, and Groq chat API.
- `scripts/run_qa.py`: isolated local stack with a credential-free chat stub.
- `frontend/e2e/`: browser regression tests against both real applications.

Detection computes matches from uploaded PNG/JPEG pixels using ten bundled
templates, at the original scale and orientation. It is not a trained general
detector. OCR is unavailable; no sample tags are displayed. Graph generation and
database integration are not implemented. See the quick start for limits and
live-chat setup.
