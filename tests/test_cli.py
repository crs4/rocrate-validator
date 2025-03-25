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
