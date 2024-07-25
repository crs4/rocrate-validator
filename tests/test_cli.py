
import re

from click.testing import CliRunner
from pytest import fixture

from rocrate_validator import log as logging
from rocrate_validator.cli.main import cli
from rocrate_validator.utils import get_version
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
        InvalidFileDescriptor().invalid_json_format), '--details', '--no-paging', '-p', 'ro-crate'])
    logger.error(result.output)
    assert result.exit_code == 1


def test_validate_subcmd_valid_local_folder_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ['validate', str(ValidROC().wrroc_paper_long_date), '--details', '--no-paging'])
    assert result.exit_code == 0
    assert re.search(r'RO-Crate.*is valid', result.output)


def test_validate_subcmd_valid_remote_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(
        cli, ['validate', str(ValidROC().sort_and_change_remote), '--details', '--no-paging'])
    assert result.exit_code == 0
    assert re.search(r'RO-Crate.*is valid', result.output)


def test_validate_subcmd_invalid_local_archive_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ['validate', str(ValidROC().sort_and_change_archive), '--details', '--no-paging'])
    assert result.exit_code == 0
    assert re.search(r'RO-Crate.*is valid', result.output)
