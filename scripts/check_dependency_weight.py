"""Measure installed dependency weight and fail on unallowlisted heavy packages.

Heavy runtime dependencies slow deploys, cold starts, and CI. This gate
measures each top-level entry of ``backend/requirements-deploy.in`` in the
local virtualenv (summing the files listed in its RECORD) and reports the
heaviest packages. A package may exceed ``BUDGET_BYTES`` only when it is
listed in ``ALLOWED_HEAVY`` with the reason it cannot be replaced.
"""

import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "backend/requirements-deploy.in"
BUDGET_BYTES = 60 * 1024 * 1024
# Deliberately heavy runtime dependencies. Keep this list short and justified.
ALLOWED_HEAVY = {
    "opencv-python-headless": (
        "Template matching needs OpenCV; the headless wheel is the smallest variant."
    ),
    "numpy": "OpenCV requires it; pinned to the current minor by the lock files.",
}


def top_level_requirements(path: Path) -> list[str]:
    names = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            names.append(stripped.split("==")[0].strip())
    return names


def installed_size_bytes(name: str) -> int:
    """Sum the installed files of a distribution via its RECORD metadata."""
    dist = distribution(name)
    total = 0
    for installed in dist.files or []:
        try:
            total += (Path(dist.locate_file(installed)).resolve()).stat().st_size
        except OSError:
            continue
    return total


def parse_deploy_description(name: str) -> str:
    return distribution(name).metadata["Summary"] or ""


def main() -> None:
    errors: list[str] = []
    weights: list[tuple[str, int]] = []
    for name in top_level_requirements(ROOT / PROFILE):
        try:
            size = installed_size_bytes(name)
        except PackageNotFoundError:
            errors.append(f"{name}: not installed in backend/venv; run make setup")
            continue
        weights.append((name, size))
        if size > BUDGET_BYTES and name not in ALLOWED_HEAVY:
            errors.append(
                f"{name}: {size / 1024 / 1024:.1f} MiB exceeds the "
                f"{BUDGET_BYTES // 1024 // 1024} MiB budget; replace, split, or justify it"
            )
        if size > BUDGET_BYTES and name in ALLOWED_HEAVY:
            print(f"allowlisted: {name} ({size / 1024 / 1024:.1f} MiB): {ALLOWED_HEAVY[name]}")
    for name, size in sorted(weights, key=lambda item: item[1], reverse=True)[:5]:
        description = parse_deploy_description(name)
        print(f"{size / 1024 / 1024:8.1f} MiB  {name}  {description}")
    total = sum(size for _, size in weights)
    print(f"{total / 1024 / 1024:8.1f} MiB  total runtime dependency weight")
    if errors:
        raise SystemExit("\n".join(errors))
    print("Runtime dependency weight is within budget")


if __name__ == "__main__":
    sys.exit(main())
