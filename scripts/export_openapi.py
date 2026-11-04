"""Export deterministic API docs without requiring credentials or real storage."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "backend"))
    with tempfile.TemporaryDirectory(prefix="pnid-schema-") as storage:
        os.environ["UPLOAD_DIR"] = storage
        os.environ["GRAPHML_PATH"] = f"{storage}/missing.graphml"
        from app.main import app

        rendered = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    destination = ROOT / "backend/openapi.json"
    if args.check:
        if not destination.exists() or destination.read_text() != rendered:
            raise SystemExit("OpenAPI schema is stale. Run make schema and include the result.")
        print("OpenAPI schema is current")
    else:
        destination.write_text(rendered)


if __name__ == "__main__":
    main()
