"""Run the real frontend/API with an isolated, explicitly fake chat provider."""
import argparse
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


class ChatStub(BaseHTTPRequestHandler):
    """Exercise the provider HTTP contract without credentials or inference."""

    def do_POST(self):
        status = 200
        try:
            if self.path != "/chat/completions":
                status = 404
                raise ValueError("Unknown stub endpoint")
            if self.headers.get("Authorization") != "Bearer local-qa-only":
                status = 401
                raise ValueError("Expected the local QA token")
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            messages = request["messages"]
            if messages[0]["role"] != "system" or not request["model"]:
                raise ValueError("Expected model and system context")
            question = messages[-1]["content"]
            if messages[-1]["role"] != "user" or not question.strip():
                raise ValueError("Expected a nonempty user question")
            body = {"choices": [{"message": {
                "role": "assistant",
                "content": f"[Local QA stub, no AI inference] Received: {question}",
            }}]}
        except (ValueError, KeyError, IndexError, TypeError):
            status = status if status != 200 else 400
            body = {"error": "Invalid local QA provider request"}
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_):
        pass


def wait_ready(url, processes, stopped, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stopped.is_set():
            raise InterruptedError
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("A QA server exited. See its output above.")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        stopped.wait(0.25)
    raise RuntimeError(f"Timed out waiting for {url}")


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend-port", type=int, default=3000)
    parser.add_argument("--backend-port", type=int, default=8000)
    args = parser.parse_args()
    ports = [args.frontend_port, args.backend_port]
    if len(set(ports)) != 2 or any(not 1024 <= port <= 65535 for port in ports):
        parser.error("Choose two different ports between 1024 and 65535.")

    for port in ports:
        with socket.socket() as probe:
            # Like the servers, allow restarting while old connections are in
            # TIME_WAIT. An active listener still makes this bind fail.
            if os.name != "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                parser.error(f"Port {port} is in use. Choose another port; do not stop unrelated servers.")

    python = ROOT / "backend/venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    next_cli = ROOT / "frontend/node_modules/next/dist/bin/next"
    node = shutil.which("node")
    if not python.exists() or not next_cli.exists() or not node:
        parser.error("Install backend/venv and frontend dependencies per QUICK_START.md first.")

    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    frontend_url = f"http://127.0.0.1:{args.frontend_port}"
    backend_url = f"http://127.0.0.1:{args.backend_port}"

    # Cleanup callbacks run in reverse: stop children before deleting their files.
    with ExitStack() as stack:
        storage = stack.enter_context(tempfile.TemporaryDirectory(prefix="pnid-qa-"))
        provider = ThreadingHTTPServer(("127.0.0.1", 0), ChatStub)
        stack.callback(provider.server_close)
        threading.Thread(target=provider.serve_forever, daemon=True).start()
        stack.callback(provider.shutdown)
        backend_env = {
            **os.environ,
            "UPLOAD_DIR": str(Path(storage) / "uploads"),
            "GRAPHML_PATH": str(Path(storage) / "no-live-graph.graphml"),
            "GROQ_API_KEY": "local-qa-only",
            "GROQ_API_URL": f"http://127.0.0.1:{provider.server_port}/chat/completions",
            "FRONTEND_URL": frontend_url,
            "ALLOW_ALL_ORIGINS": "false",
        }
        backend = subprocess.Popen(
            [str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(args.backend_port)],
            cwd=ROOT / "backend", env=backend_env,
        )
        stack.callback(stop_process, backend)
        wait_ready(f"{backend_url}/health", [backend], stopped)
        frontend = subprocess.Popen(
            [node, str(next_cli), "dev", "--hostname", "127.0.0.1",
             "--port", str(args.frontend_port)],
            cwd=ROOT / "frontend",
            env={**os.environ, "NEXT_PUBLIC_API_URL": backend_url, "NEXT_TELEMETRY_DISABLED": "1"},
        )
        stack.callback(stop_process, frontend)
        wait_ready(frontend_url, [backend, frontend], stopped)
        print(f"\nQA ready: {frontend_url}\nAPI docs: {backend_url}/docs\n"
              "Chat uses a local stub, not real inference. Uploads are temporary.\n"
              "Press Ctrl+C to stop both servers and remove QA uploads.", flush=True)
        while not stopped.wait(0.5):
            if backend.poll() is not None or frontend.poll() is not None:
                raise RuntimeError("A QA server exited. See its output above.")


if __name__ == "__main__":
    try:
        main()
    except InterruptedError:
        pass
    except (RuntimeError, OSError) as error:
        raise SystemExit(str(error))
