"""Positive and negative tests for repository consistency gates."""

import json
from types import SimpleNamespace

from check_repo import (
    LOCKS,
    dependency_errors,
    doc_errors,
    feature_flag_errors,
    pins,
    source_errors,
)


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


def flag_tree(tmp_path, sources, backend_contract="", frontend_contract=""):
    contracts = {
        "backend/.env.example": backend_contract,
        "frontend/.env.example": frontend_contract,
    }
    for name, body in contracts.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    for name, body in sources.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(body)
    return dict(sources)


def test_flag_gate_accepts_live_documented_flags(tmp_path):
    sources = flag_tree(
        tmp_path,
        {
            "backend/config.py": 'ENABLE_CHAT = os.getenv("ENABLE_CHAT", "true")\n',
            "backend/app/routers/chat.py": "from config import ENABLE_CHAT\n",
        },
        backend_contract="ENABLE_CHAT=true\n",
    )
    assert feature_flag_errors(sources, tmp_path) == []


def test_flag_gate_flags_dead_unused_switches(tmp_path):
    sources = flag_tree(
        tmp_path,
        {
            "backend/config.py": (
                'ENABLE_CHAT = os.getenv("ENABLE_CHAT", "true")\n'
                'ENABLE_METRICS = os.getenv("ENABLE_METRICS", "false")\n'
            ),
            "backend/app/routers/chat.py": "from config import ENABLE_CHAT\n",
        },
        backend_contract="ENABLE_CHAT=true\nENABLE_METRICS=false\n",
    )
    errors = feature_flag_errors(sources, tmp_path)
    assert len(errors) == 1
    assert "ENABLE_METRICS is dead" in errors[0]


def test_flag_gate_rejects_undocumented_and_undefined_flags(tmp_path):
    sources = flag_tree(
        tmp_path,
        {
            "backend/config.py": (
                'ENABLE_CHAT = os.getenv("ENABLE_CHAT", "true")\n'
                'ENABLE_LEGACY = os.getenv("ENABLE_LEGACY", "false")\n'
            ),
            "backend/app/routers/chat.py": (
                "from config import ENABLE_CHAT\nfrom config import ENABLE_LEGACY\n"
            ),
        },
        backend_contract="ENABLE_CHAT=true\nENABLE_METRICS=false\n",
    )
    errors = feature_flag_errors(sources, tmp_path)
    assert any("ENABLE_LEGACY is defined but not documented" in error for error in errors)
    assert any("ENABLE_METRICS is documented but not defined" in error for error in errors)


def test_flag_gate_ignores_test_and_script_references(tmp_path):
    sources = flag_tree(
        tmp_path,
        {
            "backend/config.py": 'ENABLE_CHAT = os.getenv("ENABLE_CHAT", "true")\n',
            "backend/tests/test_chat.py": "ENABLE_CHAT\n",
            "scripts/check_repo.py": "ENABLE_CHAT\n",
        },
        backend_contract="ENABLE_CHAT=true\n",
    )
    errors = feature_flag_errors(sources, tmp_path)
    assert any("ENABLE_CHAT is dead" in error for error in errors)


def test_flag_gate_tracks_frontend_switches(tmp_path):
    sources = flag_tree(
        tmp_path,
        {"frontend/lib/theme.test.ts": "NEXT_PUBLIC_ENABLE_DARK_MODE\n"},
        frontend_contract="NEXT_PUBLIC_ENABLE_DARK_MODE=false\n",
    )
    errors = feature_flag_errors(sources, tmp_path)
    assert any("NEXT_PUBLIC_ENABLE_DARK_MODE is dead" in error for error in errors)
    live = dict(sources)
    live["frontend/lib/theme.ts"] = "if (process.env.NEXT_PUBLIC_ENABLE_DARK_MODE) enable();\n"
    assert feature_flag_errors(live, tmp_path) == []
