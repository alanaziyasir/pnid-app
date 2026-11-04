"""Record build duration and exit status while retaining normal console output."""

import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    command = sys.argv[1:]
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise SystemExit("Usage: time_build.py -- COMMAND [ARG ...]")
    started = time.monotonic()
    result = subprocess.run(command, check=False)
    metrics = {
        "duration_seconds": round(time.monotonic() - started, 3),
        "exit_code": result.returncode,
    }
    report = Path(__file__).resolve().parents[1] / "reports/build.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics), flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
