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

import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

from rocrate_validator.constants import PACKAGE_NAME
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.config import get_config, get_config_path

# set up logging
logger = logging.getLogger(__name__)


def run_git_command(command: list[str], cwd: Path | None = None) -> str | None:
    """
    Run a git command and return the output

    :param command: The git command
    :param cwd: The directory in which to run the command
    :return: The output of the command
    """

    try:
        return subprocess.check_output(command, cwd=cwd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(e)
        return None


def get_git_commit(cwd: Path | None = None) -> str:
    """
    Get the git commit hash

    :param cwd: The directory of the git repository
    :return: The git commit hash
    """
    return run_git_command(["git", "rev-parse", "--short", "HEAD"], cwd=cwd) or ""


def is_release_tag(git_sha: str, cwd: Path | None = None) -> bool:
    """
    Check whether a git sha corresponds to a release tag

    :param git_sha: The git sha
    :param cwd: The directory of the git repository
    :return: True if the sha corresponds to a release tag, False otherwise
    """
    tags = run_git_command(["git", "tag", "--points-at", git_sha], cwd=cwd)
    return bool(tags)


def get_last_tag(cwd: Path | None = None) -> str:
    """
    Get the last tag in the git repository

    :param cwd: The directory of the git repository
    :return: The last tag
    """
    return run_git_command(["git", "describe", "--tags", "--abbrev=0"], cwd=cwd) or ""


def get_commit_distance(tag: str | None = None, cwd: Path | None = None) -> int:
    """
    Get the distance in commits between the current commit and the last tag

    :param tag: The tag from which to count
    :param cwd: The directory of the git repository
    :return: The distance in commits
    """
    if not tag:
        tag = get_last_tag(cwd=cwd)
    try:
        count = run_git_command(["git", "rev-list", "--count", f"{tag}..HEAD"], cwd=cwd)
        return int(count) if count else 0
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(e)

    return 0


def has_uncommitted_changes(cwd: Path | None = None) -> bool:
    """
    Check whether there are any uncommitted changes in the repository

    :param cwd: The directory of the git repository
    :return: True if there are uncommitted changes, False otherwise
    """
    return bool(run_git_command(["git", "status", "--porcelain"], cwd=cwd))


def _is_source_checkout(package_root: Path) -> bool:
    """Return whether the package files belong to their own Git checkout."""
    if not (package_root / ".git").exists():
        return False

    git_root = run_git_command(["git", "rev-parse", "--show-toplevel"], cwd=package_root)
    return bool(git_root) and Path(git_root).resolve() == package_root.resolve()


def get_version() -> str:
    """
    Get the version of the package

    :return: The version
    """
    package_root = get_config_path().parent
    source_checkout = _is_source_checkout(package_root)

    if not source_checkout:
        try:
            return metadata.version(PACKAGE_NAME)
        except metadata.PackageNotFoundError:
            pass

    config = get_config()
    declared_version = config["tool"]["poetry"]["version"]
    if not source_checkout:
        return declared_version

    commit_sha = get_git_commit(cwd=package_root)
    is_release = is_release_tag(commit_sha, cwd=package_root)
    latest_tag = get_last_tag(cwd=package_root)
    if is_release:
        if declared_version != latest_tag:
            logger.warning("The declared version %s is different from the last tag %s", declared_version, latest_tag)
        version = latest_tag
    else:
        commit_distance = get_commit_distance(latest_tag, cwd=package_root)
        version = f"{declared_version}_{commit_sha}+{commit_distance}" if commit_sha else declared_version
    dirty = has_uncommitted_changes(cwd=package_root)
    return f"{version}-dirty" if dirty else version


def get_min_python_version() -> tuple[int, ...]:
    """
    Get the minimum Python version required by the package

    :return: The minimum Python version
    """
    config = get_config()
    min_version_str = config["tool"]["poetry"]["dependencies"]["python"]
    assert min_version_str, "The minimum Python version is required"
    # remove any non-digit characters
    min_version_str = re.sub(r"[^\d.]+", "", min_version_str)
    # convert the version string to a tuple
    min_version = tuple(map(int, min_version_str.split(".")))
    logger.debug(f"Minimum Python version: {min_version}")
    return min_version


def check_python_version() -> bool:
    """
    Check if the current Python version meets the minimum requirements
    """
    return sys.version_info >= get_min_python_version()
