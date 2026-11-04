"""Validate commands, local links, debt markers, sizes, feature flags, and versions."""

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
FLAG_NAME = re.compile(r"\b(?:ENABLE|NEXT_PUBLIC_ENABLE)_[A-Z0-9_]+\b")


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


def is_application_source(path: str) -> bool:
    """Flag usage must be live application code, not tests or the check itself."""
    if path.startswith(("backend/tests/", "scripts/")) or path == "backend/config.py":
        return False
    if ".test." in path or path.startswith("frontend/e2e/"):
        return False
    return path.startswith(("backend/", "frontend/"))


def feature_flag_errors(sources: dict[str, str], root: Path) -> list[str]:
    """Detect dead flags: defined but unused, or undocumented in the env contract.

    A feature flag is an `ENABLE_*` backend switch or a `NEXT_PUBLIC_ENABLE_*`
    frontend switch. Each one must be defined in code, documented in the
    matching `.env.example`, and referenced by at least one application file
    other than its definition. Otherwise it is dead and should be removed.
    """
    errors: list[str] = []
    for contract, definition_file in (
        ("backend/.env.example", "backend/config.py"),
        ("frontend/.env.example", "frontend"),
    ):
        contract_flags = set(FLAG_NAME.findall((root / contract).read_text()))
        if definition_file == "backend/config.py":
            defined_flags = set(FLAG_NAME.findall(sources.get(definition_file, "")))
        else:
            defined_flags = {
                name
                for path, body in sources.items()
                if path.startswith("frontend/") and path.endswith((".ts", ".tsx"))
                for name in FLAG_NAME.findall(body)
            }
        for name in sorted(contract_flags - defined_flags):
            errors.append(f"{contract}: feature flag {name} is documented but not defined")
        for name in sorted(defined_flags - contract_flags):
            errors.append(f"{contract}: feature flag {name} is defined but not documented")
        for name in sorted(defined_flags & contract_flags):
            uses = [
                path
                for path, body in sources.items()
                if is_application_source(path) and name in body
            ]
            if not uses:
                errors.append(
                    f"feature flag {name} is dead: only defined in {definition_file}; "
                    "remove it or wire it into application code"
                )
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
    sources: dict[str, str] = {}
    for name in set(result.stdout.decode().split("\0")) - {""}:
        path = ROOT / name
        # Ignore user-generated, untracked QA evidence. Tracked output still has
        # the size hook; application source and configuration are checked here.
        if path.is_file() and not name.startswith(("outputs/", "tmp/")):
            errors.extend(source_errors(path, ROOT))
            if name.endswith((".py", ".ts", ".tsx", ".js", ".mjs")):
                sources[name] = path.read_text()
    errors.extend(feature_flag_errors(sources, ROOT))
    if errors:
        raise SystemExit("\n".join(errors))
    print("Docs, commands, file sizes, debt markers, feature flags, and versions are consistent")


if __name__ == "__main__":
    main()
