"""Validate documented commands, local links, debt markers, sizes, and version drift."""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCKS = (
    "backend/requirements-deploy.txt",
    "backend/requirements_minimal.txt",
    "backend/requirements.txt",
    "requirements-dev.txt",
)
PIN = re.compile(r"^([\w.-]+)(?:\[[^]]+\])?==([^\s;\\]+)", re.MULTILINE)
DEBT = re.compile(
    r"^\s*(?:#|//|/\*|\*)\s*.*?\b(?:TODO|FIXME)\b(?!\(https://github\.com/alanaziyasir/pnid-app/issues/\d+\))"
)


def pins(text: str) -> dict[str, str]:
    return {re.sub(r"[-_.]+", "-", name.lower()): version for name, version in PIN.findall(text)}


def dependency_errors(root: Path) -> list[str]:
    seen: dict[str, tuple[str, str]] = {}
    errors = []
    for name in LOCKS:
        body = (root / name).read_text()
        for number, line in enumerate(body.splitlines(), 1):
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "--hash=")) and not PIN.match(stripped):
                errors.append(f"{name}:{number}: lock dependency is not pinned")
        for dependency, version in pins(body).items():
            if dependency in seen and seen[dependency][0] != version:
                errors.append(
                    f"Version drift: {dependency}: {seen[dependency]} vs {(version, name)}"
                )
            seen[dependency] = (version, name)
    for source, lock in (
        ("backend/requirements-deploy.in", "backend/requirements-deploy.txt"),
        ("requirements-dev.in", "requirements-dev.txt"),
    ):
        locked = pins((root / lock).read_text())
        for dependency, version in pins((root / source).read_text()).items():
            if locked.get(dependency) != version:
                errors.append(f"{source}: {dependency} does not match {lock}")
    package = json.loads((root / "frontend/package.json").read_text())
    lock = json.loads((root / "frontend/package-lock.json").read_text())["packages"][""]
    for field in ("dependencies", "devDependencies"):
        if package.get(field, {}) != lock.get(field, {}):
            errors.append(f"Frontend {field} drifted from package-lock.json")
    return errors


def doc_errors(root: Path) -> list[str]:
    errors = []
    for name in ("README.md", "AGENTS.md", "CONTRIBUTING.md", "QUALITY.md"):
        body = (root / name).read_text()
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", body):
            if (
                "://" not in target
                and not target.startswith("#")
                and not (root / target.split("#")[0]).exists()
            ):
                errors.append(f"{name}: broken local link: {target}")
    commands = re.findall(r"^make ([\w-]+)$", (root / "AGENTS.md").read_text(), re.MULTILINE)
    if not commands:
        errors.append("AGENTS.md must document runnable make commands")
    for command in commands:
        result = subprocess.run(
            ["make", "--dry-run", command], cwd=root, capture_output=True, check=False
        )
        if result.returncode:
            errors.append(f"AGENTS.md command no longer exists: make {command}")
    return errors


def source_errors(path: Path, root: Path) -> list[str]:
    errors = []
    if path.stat().st_size > 1024 * 1024:
        errors.append(f"{path.relative_to(root)} exceeds 1 MiB")
    if path.suffix in {".py", ".ts", ".tsx", ".js", ".mjs"}:
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if DEBT.search(line):
                errors.append(f"{path.relative_to(root)}:{number}: debt marker needs an issue URL")
    return errors


def main() -> None:
    errors = dependency_errors(ROOT) + doc_errors(ROOT)
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    for name in set(result.stdout.decode().split("\0")) - {""}:
        path = ROOT / name
        # Ignore user-generated, untracked QA evidence. Tracked output still has
        # the size hook; application source and configuration are checked here.
        if path.is_file() and not name.startswith(("outputs/", "tmp/")):
            errors.extend(source_errors(path, ROOT))
    if errors:
        raise SystemExit("\n".join(errors))
    print("Docs, command targets, file sizes, debt markers, and dependency versions are consistent")


if __name__ == "__main__":
    main()
