# Copyright (c) 2024-2026 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from rocrate_validator.utils import versioning

PACKAGE_VERSION = versioning.get_config()["tool"]["poetry"]["version"]


def _version_config(version: str = PACKAGE_VERSION) -> dict:
    return {"tool": {"poetry": {"version": version}}}


def _run_git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_get_version_uses_distribution_metadata_outside_source_checkout(monkeypatch, tmp_path: Path):
    package_root = tmp_path / "site-packages"
    package_root.mkdir()
    monkeypatch.setattr(versioning, "get_config_path", lambda: package_root / "pyproject.toml")
    monkeypatch.setattr(versioning, "_is_source_checkout", lambda _: False)
    monkeypatch.setattr(versioning.metadata, "version", lambda name: PACKAGE_VERSION)
    run_git_command = Mock(side_effect=AssertionError("Git must not be queried for an installed package"))
    get_config = Mock(side_effect=AssertionError("pyproject.toml is not needed when metadata is available"))
    monkeypatch.setattr(versioning, "run_git_command", run_git_command)
    monkeypatch.setattr(versioning, "get_config", get_config)

    assert versioning.get_version() == PACKAGE_VERSION
    run_git_command.assert_not_called()
    get_config.assert_not_called()


def test_get_version_falls_back_to_declared_version_when_metadata_is_missing(monkeypatch, tmp_path: Path):
    package_root = tmp_path / "source-distribution"
    package_root.mkdir()
    monkeypatch.setattr(versioning, "get_config_path", lambda: package_root / "pyproject.toml")
    monkeypatch.setattr(versioning, "_is_source_checkout", lambda _: False)

    def missing_distribution(name: str) -> str:
        raise versioning.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(versioning.metadata, "version", missing_distribution)
    monkeypatch.setattr(versioning, "get_config", _version_config)

    assert versioning.get_version() == PACKAGE_VERSION


def test_get_version_anchors_source_checkout_git_commands(monkeypatch, tmp_path: Path):
    package_root = tmp_path / "rocrate-validator"
    package_root.mkdir()
    monkeypatch.setattr(versioning, "get_config_path", lambda: package_root / "pyproject.toml")
    monkeypatch.setattr(versioning, "_is_source_checkout", lambda _: True)
    monkeypatch.setattr(versioning.metadata, "version", lambda _: pytest.fail("Source checkouts must use Git"))
    monkeypatch.setattr(versioning, "get_config", _version_config)

    outputs = iter(["abc1234", "", PACKAGE_VERSION, "7", ""])
    calls: list[tuple[list[str], Path | None]] = []

    def run_git_command(command: list[str], cwd: Path | None = None) -> str:
        calls.append((command, cwd))
        return next(outputs)

    monkeypatch.setattr(versioning, "run_git_command", run_git_command)

    assert versioning.get_version() == f"{PACKAGE_VERSION}_abc1234+7"
    assert len(calls) == 5
    assert all(cwd == package_root for _, cwd in calls)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required for the consumer-repository regression")
def test_source_import_ignores_consumer_repository_tag(tmp_path: Path):
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _run_git(consumer, "init", "--quiet")
    _run_git(
        consumer,
        "-c",
        "user.name=Issue 198 Test",
        "-c",
        "user.email=issue-198@example.invalid",
        "-c",
        "commit.gpgSign=false",
        "commit",
        "--allow-empty",
        "--quiet",
        "-m",
        "consumer release",
    )
    _run_git(consumer, "tag", "0.3.1")

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    result = subprocess.run(
        [sys.executable, "-c", "import rocrate_validator; print(rocrate_validator.__version__)"],
        cwd=consumer,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "0.3.1" not in output
    assert "different from the last tag" not in output
