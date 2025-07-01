# Copyright (c) 2024-2025 CRS4
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
from pathlib import Path

from click.testing import CliRunner
from pytest import fixture

from rocrate_validator import log as logging
from rocrate_validator.cli.main import cli
from rocrate_validator.utils import get_version
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import InvalidFileDescriptor, ValidROC

# set up logging
logger = logging.getLogger(__name__)


@fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_version(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert get_version() in result.output


def test_validate_subcmd_invalid_rocrate1(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ['validate', str(
        InvalidFileDescriptor().invalid_json_format), '--verbose', '--no-paging', '-p', 'ro-crate'])
    logger.error(result.output)
    assert result.exit_code == 1


def test_validate_subcmd_valid_local_folder_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ['validate', str(ValidROC().wrroc_paper_long_date), '--verbose', '--no-paging'])
    assert result.exit_code == 0
    assert re.search(r'RO-Crate.*is a valid', result.output)


def test_validate_subcmd_valid_remote_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(
        cli, ['validate', str(ValidROC().sort_and_change_remote),
              '--verbose', '--no-paging',
              '--skip-checks', SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER])
    assert result.exit_code == 0
    assert re.search(r'RO-Crate.*is a valid', result.output)


def test_validate_subcmd_invalid_local_archive_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ['validate', str(ValidROC().sort_and_change_archive),
                                     '--verbose', '--no-paging',
                                     '--skip-checks', SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER])
    assert result.exit_code == 0
    assert re.search(r'RO-Crate.*is a valid', result.output)


def test_validate_with_invalid_profiles_path_dir(cli_runner: CliRunner):
    # Create a directory with a dummy profile file
    dummy_profiles_path = "/tmp/dummy_profiles"
    result = cli_runner.invoke(
        cli,
        [
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--profiles-path", dummy_profiles_path,
            "--verbose",
            "--no-paging"
        ]
    )
    assert result.exit_code == 2
    # logger.debug(result.output)
    assert re.search(f"Path '{dummy_profiles_path}' does not exist.", result.output)


def test_profiles_list(cli_runner: CliRunner):
    """
    Test the list of profiles.
    """
    result = cli_runner.invoke(cli, ["profiles", "list", "--no-paging"])
    # logger.debug("Profiles list output: %s", result.output)
    assert result.exit_code == 0
    # assert "Available profiles:" in result.output
    assert "ro-crate-1.1" in result.output  # Check for a known profile


def test_extra_profiles_list(cli_runner: CliRunner, fake_profiles_path: Path):
    """
    Test the list of extra profiles.
    """
    result = cli_runner.invoke(cli, ["profiles", "--extra-profiles-path", fake_profiles_path, "list", "--no-paging"])
    # logger.debug("Extra profiles list output: %s", result.output)
    assert result.exit_code == 0
    # assert "Available profiles:" in result.output
    assert "Profile A" in result.output  # Check for a known extra profile
