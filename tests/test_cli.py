
from click.testing import CliRunner
from pytest import fixture

from rocrate_validator.cli.main import cli
from rocrate_validator.utils import get_version
from tests.ro_crates import InvalidFileDescriptor, ValidROC


@fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_version(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert get_version() in result.output


def test_validate_subcmd_valid_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ['validate', str(ValidROC().wrroc_paper_long_date)])
    assert result.exit_code == 0
    assert 'RO-Crate is valid' in result.output


def test_validate_subcmd_invalid_rocrate1(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ['validate', str(InvalidFileDescriptor().invalid_json_format)])
    assert result.exit_code == 1
