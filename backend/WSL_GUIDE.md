# WSL Quick Start Guide

## Starting WSL (Ubuntu)

Open PowerShell or Windows Terminal and run:
```bash
wsl
```

## Activating Virtual Environment

```bash
# Activate the venv (from anywhere)
source ~/venv_pnid/bin/activate

# Navigate to backend directory
cd /mnt/c/Users/YasirAlanazi/dev/pnid/backend
```

## Running the Backend Server

```bash
# Make sure venv is activated (you should see (venv_pnid) in your prompt)
source ~/venv_pnid/bin/activate

# Navigate to backend
cd /mnt/c/Users/YasirAlanazi/dev/pnid/backend

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## One-Line Quick Start

```bash
wsl bash -c "source ~/venv_pnid/bin/activate && cd /mnt/c/Users/YasirAlanazi/dev/pnid/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
```

## Deactivating Virtual Environment

```bash
deactivate
```


