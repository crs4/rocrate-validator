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
import sys
from typing import Optional

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.config import get_config

# set up logging
logger = logging.getLogger(__name__)


def run_git_command(command: list[str]) -> Optional[str]:
    """
    Run a git command and return the output

    :param command: The git command
    :return: The output of the command
    """
    import subprocess

    try:
        output = subprocess.check_output(command, stderr=subprocess.DEVNULL).decode().strip()
        return output
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(e)
        return None


def get_git_commit() -> str:
    """
    Get the git commit hash

    :return: The git commit hash
    """
    return run_git_command(['git', 'rev-parse', '--short', 'HEAD'])


def is_release_tag(git_sha: str) -> bool:
    """
    Check whether a git sha corresponds to a release tag

    :param git_sha: The git sha
    :return: True if the sha corresponds to a release tag, False otherwise
    """
    tags = run_git_command(['git', 'tag', '--points-at', git_sha])
    return bool(tags)


def get_last_tag() -> str:
    """
    Get the last tag in the git repository

    :return: The last tag
    """
    return run_git_command(['git', 'describe', '--tags', '--abbrev=0'])


def get_commit_distance(tag: Optional[str] = None) -> int:
    """
    Get the distance in commits between the current commit and the last tag

    :return: The distance in commits
    """
    if not tag:
        tag = get_last_tag()
    try:
        return int(run_git_command(['git', 'rev-list', '--count', f"{tag}..HEAD"]))
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(e)

    return 0


def has_uncommitted_changes() -> bool:
    """
    Check whether there are any uncommitted changes in the repository

    :return: True if there are uncommitted changes, False otherwise
    """
    return bool(run_git_command(['git', 'status', '--porcelain']))


def get_version() -> str:
    """
    Get the version of the package

    :return: The version
    """
    version = None
    config = get_config()
    declared_version = config["tool"]["poetry"]["version"]
    commit_sha = get_git_commit()
    is_release = is_release_tag(commit_sha)
    latest_tag = get_last_tag()
    if is_release:
        if declared_version != latest_tag:
            logger.warning("The declared version %s is different from the last tag %s", declared_version, latest_tag)
        version = latest_tag
    else:
        commit_distance = get_commit_distance(latest_tag)
        if commit_sha:
            version = f"{declared_version}_{commit_sha}+{commit_distance}"
        else:
            version = declared_version
    dirty = has_uncommitted_changes()
    return f"{version}-dirty" if dirty else version


def get_min_python_version() -> tuple[int, int, Optional[int]]:
    """
    Get the minimum Python version required by the package

    :return: The minimum Python version
    """
    config = get_config()
    min_version_str = config["tool"]["poetry"]["dependencies"]["python"]
    assert min_version_str, "The minimum Python version is required"
    # remove any non-digit characters
    min_version_str = re.sub(r'[^\d.]+', '', min_version_str)
    # convert the version string to a tuple
    min_version = tuple(map(int, min_version_str.split(".")))
    logger.debug(f"Minimum Python version: {min_version}")
    return min_version


def check_python_version() -> bool:
    """
    Check if the current Python version meets the minimum requirements
    """
    return sys.version_info >= get_min_python_version()
