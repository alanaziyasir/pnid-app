"""Regression tests for the local-only provider and launcher safety checks."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from run_qa import ChatStub, ThreadingHTTPServer, stop_process
from unittest.mock import Mock


class ChatStubTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ChatStub)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join)
        self.addCleanup(self.server.shutdown)

    def post(self, payload, token="local-qa-only", endpoint="/chat/completions"):
        request = Request(
            f"http://127.0.0.1:{self.server.server_port}{endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
        try:
            response = urlopen(request, timeout=2)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_contract_returns_explicit_stub_response(self):
        status, body = self.post({
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "P&ID context"},
                {"role": "user", "content": "Which components?"},
            ],
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["choices"][0]["message"], {
            "role": "assistant",
            "content": "[Local QA stub, no AI inference] Received: Which components?",
        })

    def test_rejects_missing_system_context(self):
        self.assertEqual(self.post({
            "model": "test", "messages": [{"role": "user", "content": "Question"}],
        })[0], 400)

    def test_rejects_real_credentials_and_unknown_paths(self):
        self.assertEqual(self.post({}, token="not-a-qa-token")[0], 401)
        self.assertEqual(self.post({}, endpoint="/other")[0], 404)


class LauncherTests(unittest.TestCase):
    def launch(self, *args):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("run_qa.py")), *args],
            capture_output=True, text=True, timeout=5,
        )

    def test_rejects_duplicate_ports(self):
        result = self.launch("--frontend-port", "3100", "--backend-port", "3100")
        self.assertEqual(result.returncode, 2)
        self.assertIn("two different ports", result.stderr)

    def test_does_not_reuse_occupied_port(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            other_port = 8101 if port != 8101 else 8102
            result = self.launch("--frontend-port", str(port), "--backend-port", str(other_port))
            self.assertEqual(result.returncode, 2)
            self.assertIn(f"Port {port} is in use", result.stderr)

    def test_cleanup_kills_child_if_graceful_shutdown_times_out(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("child", 10), 0]
        stop_process(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
