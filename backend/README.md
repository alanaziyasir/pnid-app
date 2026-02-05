# P&ID Digitization Backend

FastAPI backend for processing P&ID diagrams.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate virtual environment:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app initialization
│   └── routers/
│       ├── __init__.py
│       └── upload.py     # File upload endpoints
├── uploads/              # Uploaded files storage
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
└── README.md
```

## API Endpoints

### Upload File
- **POST** `/api/upload`
- Upload a P&ID diagram file
- Accepts: .pdf, .dwg, .dgn, .jpg, .png, .zip, .svg, .xml
- Max size: 50MB

### List Files
- **GET** `/api/files`
- Get list of all uploaded files

### Health Check
- **GET** `/health`
- Check API health status

