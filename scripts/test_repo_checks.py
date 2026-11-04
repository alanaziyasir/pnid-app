"""Positive and negative tests for repository consistency gates."""

import json
from types import SimpleNamespace

from check_repo import LOCKS, dependency_errors, doc_errors, pins, source_errors


def manifests(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    for name in (*LOCKS, "backend/requirements-deploy.in", "requirements-dev.in"):
        (tmp_path / name).write_text("httpx==0.28.1 \\\n    --hash=sha256:example\n")
    package = {"dependencies": {"next": "^15.5.10"}}
    (tmp_path / "frontend/package.json").write_text(json.dumps(package))
    (tmp_path / "frontend/package-lock.json").write_text(json.dumps({"packages": {"": package}}))


def test_pins_normalize_names_and_ignore_hashes():
    assert pins("typing_extensions==4.16.0 \\\n --hash=sha256:abc\n# comment\n") == {
        "typing-extensions": "4.16.0"
    }


def test_dependency_gate_accepts_aligned_profiles(tmp_path):
    manifests(tmp_path)
    assert dependency_errors(tmp_path) == []


def test_dependency_gate_detects_cross_profile_drift(tmp_path):
    manifests(tmp_path)
    (tmp_path / LOCKS[1]).write_text("httpx==0.27.0\n")
    assert any("Version drift: httpx" in error for error in dependency_errors(tmp_path))


def test_dependency_gate_rejects_floating_lock_entries(tmp_path):
    manifests(tmp_path)
    (tmp_path / LOCKS[1]).write_text("httpx>=0.28\n")
    assert any("not pinned" in error for error in dependency_errors(tmp_path))


def test_dependency_gate_detects_input_and_npm_lock_drift(tmp_path):
    manifests(tmp_path)
    (tmp_path / "requirements-dev.in").write_text("httpx==0.27.0\n")
    (tmp_path / "frontend/package.json").write_text(
        json.dumps({"dependencies": {"next": "^15.5.28"}})
    )
    errors = dependency_errors(tmp_path)
    assert any("does not match" in error for error in errors)
    assert any("Frontend dependencies drifted" in error for error in errors)


def test_source_gate_requires_issue_links_and_checks_file_sizes(tmp_path):
    path = tmp_path / "example.py"
    path.write_text(
        "# TODO implement\n# FIXME(https://github.com/alanaziyasir/pnid-app/issues/123) tracked\n"
    )
    errors = source_errors(path, tmp_path)
    assert len(errors) == 1
    assert ":1:" in errors[0]
    path.write_bytes(b"x" * (1024 * 1024 + 1))
    assert any("exceeds 1 MiB" in error for error in source_errors(path, tmp_path))


def test_docs_gate_checks_links_and_make_targets(tmp_path, monkeypatch):
    for name in ("README.md", "AGENTS.md", "CONTRIBUTING.md", "QUALITY.md"):
        (tmp_path / name).write_text("[broken](missing.md)\nmake obsolete\n")
    monkeypatch.setattr(
        "check_repo.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=2)
    )
    errors = doc_errors(tmp_path)
    assert any("broken local link" in error for error in errors)
    assert any("make obsolete" in error for error in errors)
