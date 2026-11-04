"""Keep native update jobs usable without overlapping Python profile updates."""

import json
import re
from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def dependabot_updates():
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
    assert config["version"] == 2
    updates = {update["package-ecosystem"]: update for update in config["updates"]}
    assert len(updates) == len(config["updates"])
    return updates


def test_dependabot_targets_existing_native_ecosystems():
    updates = dependabot_updates()
    assert set(updates) == {"npm", "github-actions"}
    frontend = ROOT / updates["npm"]["directory"].lstrip("/")
    assert frontend == ROOT / "frontend"
    package = json.loads((frontend / "package.json").read_text())
    lock = json.loads((frontend / "package-lock.json").read_text())
    assert package["dependencies"] == lock["packages"][""]["dependencies"]
    assert updates["github-actions"]["directory"] == "/"
    assert list((ROOT / ".github/workflows").glob("*.yml"))


@pytest.mark.parametrize("ecosystem", ["npm", "github-actions"])
def test_version_updates_are_scheduled_and_respect_release_age(ecosystem):
    update = dependabot_updates()[ecosystem]
    assert update["schedule"]["interval"] == "weekly"
    assert update["schedule"]["day"] == "monday"
    assert update["schedule"]["timezone"] == "Etc/UTC"
    assert re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", update["schedule"]["time"])
    assert update["cooldown"] == {"default-days": 7}
    assert 0 < update["open-pull-requests-limit"] <= 5
    assert "target-branch" not in update  # Native PRs must exercise default-branch CI.


@pytest.mark.parametrize("ecosystem", ["npm", "github-actions"])
def test_minor_patch_groups_leave_major_updates_for_separate_review(ecosystem):
    update = dependabot_updates()[ecosystem]
    assert update["groups"]
    for group in update["groups"].values():
        assert group["patterns"] == ["*"]
        assert set(group["update-types"]) == {"minor", "patch"}
    assert update["commit-message"] == {"prefix": "chore", "include": "scope"}


def test_renovate_does_not_duplicate_native_updates_or_rewrite_python_locks():
    config = json.loads((ROOT / "renovate.json").read_text())
    assert config["enabledManagers"] == ["pip_requirements"]
    assert config["minimumReleaseAge"] == "7 days"
    assert config["automerge"] is False
    assert all(rule["matchManagers"] == ["pip_requirements"] for rule in config["packageRules"])
    patterns = config["pip_requirements"]["managerFilePatterns"]
    inputs = list(ROOT.glob("requirements*.in")) + list((ROOT / "backend").glob("requirements*.in"))
    locks = list(ROOT.glob("requirements*.txt")) + list(
        (ROOT / "backend").glob("requirements*.txt")
    )
    assert len(inputs) == 4
    for path in inputs:
        assert any(
            fnmatchcase(path.relative_to(ROOT).as_posix(), pattern)
            for pattern in config["includePaths"]
        )
        assert any(
            re.search(pattern[1:-1], path.relative_to(ROOT).as_posix()) for pattern in patterns
        )
    for path in locks:
        assert not any(
            fnmatchcase(path.relative_to(ROOT).as_posix(), pattern)
            for pattern in config["includePaths"]
        )
