"""Positive and negative tests for the dependency weight gate."""

import check_dependency_weight as gate
import pytest


def test_top_level_requirements_skips_comments_and_versions(tmp_path):
    path = tmp_path / "requirements-deploy.in"
    path.write_text("# comment\nfastapi==0.162.0\nopencv-python-headless==5.0.0.93\n")
    assert gate.top_level_requirements(path) == ["fastapi", "opencv-python-headless"]


def write_profile(tmp_path):
    tmp_path.joinpath(gate.PROFILE).parent.mkdir(parents=True, exist_ok=True)
    tmp_path.joinpath(gate.PROFILE).write_text("heavy==1.0.0\nlight==1.0.0\n")


def test_gate_flags_unallowlisted_heavy_dependency(tmp_path, monkeypatch, capsys):
    write_profile(tmp_path)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "ALLOWED_HEAVY", {})
    monkeypatch.setattr(
        gate,
        "installed_size_bytes",
        lambda name: {"heavy": 70 * 1024 * 1024, "light": 1024}[name],
    )
    monkeypatch.setattr(gate, "parse_deploy_description", lambda name: "stub description")
    with pytest.raises(SystemExit) as failure:
        gate.main()
    assert "heavy: 70.0 MiB exceeds the" in str(failure.value)
    assert "MiB" in capsys.readouterr().out


def test_gate_accepts_allowlisted_heavy_dependency(tmp_path, monkeypatch, capsys):
    write_profile(tmp_path)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "ALLOWED_HEAVY", {"heavy": "needed for template matching"})
    monkeypatch.setattr(
        gate,
        "installed_size_bytes",
        lambda name: {"heavy": 70 * 1024 * 1024, "light": 1024}[name],
    )
    monkeypatch.setattr(gate, "parse_deploy_description", lambda name: "stub description")
    gate.main()
    output = capsys.readouterr().out
    assert "allowlisted: heavy" in output
    assert "within budget" in output


def test_gate_reports_missing_installs(tmp_path, monkeypatch):
    write_profile(tmp_path)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "ALLOWED_HEAVY", {})
    monkeypatch.setattr(
        gate,
        "installed_size_bytes",
        lambda name: (_ for _ in ()).throw(gate.PackageNotFoundError(name)),
    )
    with pytest.raises(SystemExit) as failure:
        gate.main()
    assert "not installed" in str(failure.value)
