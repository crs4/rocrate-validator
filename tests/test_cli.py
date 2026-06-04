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
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from pytest import fixture

from rocrate_validator import services
from rocrate_validator.cli.main import cli
from rocrate_validator.requirements.python import PyFunctionCheck
from rocrate_validator.requirements.shacl.checks import SHACLCheck
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.versioning import get_version
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import InvalidFileDescriptor, ValidROC

# set up logging
logger = logging.getLogger(__name__)


@fixture
def cli_runner() -> CliRunner:
    # Force a wide terminal: the CLI renders output through Rich, which wraps
    # and truncates tables/panels to the terminal width (defaulting to 80
    # columns when stdout is captured). Pinning COLUMNS keeps the rendered
    # output deterministic regardless of the environment's actual width.
    return CliRunner(env={"COLUMNS": "200"})


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


def test_validate_skip_checks_option(cli_runner: CliRunner):
    # Patch the validation service to capture the skip_checks argument
    called_args = []
    called_kwargs = {}

    def mock_validate(*args, **kwargs):
        nonlocal called_args

        logger.warning(f"Mock validate called with args: {args}, kwargs: {kwargs}")

        called_args.extend(args)
        called_kwargs.update(kwargs)

        logger.debug(f"Args: {args}")
        logger.debug(f"Kwargs: {kwargs}")
        logger.debug(f"Called args: {called_args}")
        logger.debug(f"Called kwargs: {called_kwargs}")

    with patch('rocrate_validator.cli.commands.validate.services.validate') as mock_validate_rocrate:
        mock_validate_rocrate.return_value = None
        mock_validate_rocrate.side_effect = mock_validate

        skip_checks_1 = ("a", "b", "c")
        skip_checks_2 = ("d", "e", "f")
        result = cli_runner.invoke(
            cli, [
                '--no-interactive',
                'validate', str(ValidROC().sort_and_change_remote),
                '--skip-checks', ','.join(skip_checks_1),
                '--skip-checks', ','.join(skip_checks_2),
                '--no-paging'
            ]
        )

        # Check the exit code which should be 2
        # because the validation service is mocked and does not return a valid result
        assert result.exit_code == 2
        # Check if 'skip_checks' is in the called arguments
        settings = called_args[0]
        assert isinstance(settings, dict), "Validation settings should be a dictionary"

        # Check if the skip_checks attribute is not None
        assert settings["skip_checks"] is not None, "skip_checks should not be None"

        # Check if the skip_checks value matches the expected value
        assert list(skip_checks_1 + skip_checks_2) == settings["skip_checks"], \
            f"Expected skip_checks to be {list(skip_checks_1 + skip_checks_2)}, but got {settings.skip_checks}"


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
    # On narrow terminals the Rich error panel wraps the message across lines
    # and inserts box-drawing borders (│) between words; strip those and
    # collapse whitespace so the match does not depend on terminal width.
    normalized_output = re.sub(r"[\s│]+", " ", result.output)
    assert re.search(f"Path '{dummy_profiles_path}' does not exist.", normalized_output)


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


# Profile used for `profiles describe` tests.
_DESCRIBE_TEST_PROFILE = "ro-crate-1.1"


def _first_visible_check():
    """Return the first non-hidden (Python-backed) check of the test profile."""
    profile = services.get_profile(_DESCRIBE_TEST_PROFILE)
    for requirement in profile.requirements:
        if requirement.hidden:
            continue
        for check in requirement.get_checks():
            if isinstance(check, PyFunctionCheck):
                return profile, requirement, check
    raise RuntimeError("No Python-backed check found in test profile")


def _first_shacl_check():
    """Return the first non-hidden SHACL-backed check of the test profile."""
    profile = services.get_profile(_DESCRIBE_TEST_PROFILE)
    for requirement in profile.requirements:
        if requirement.hidden:
            continue
        for check in requirement.get_checks():
            if isinstance(check, SHACLCheck):
                return profile, requirement, check
    raise RuntimeError("No SHACL-backed check found in test profile")


def test_profiles_describe_default(cli_runner: CliRunner):
    """The default describe view (no check id) shows the profile compact view."""
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, "--no-paging"])
    assert result.exit_code == 0
    assert _DESCRIBE_TEST_PROFILE in result.output
    assert "Profile Requirements" in result.output


def test_profiles_describe_verbose(cli_runner: CliRunner):
    """The verbose describe view (no check id) shows individual check identifiers."""
    _, _, check = _first_visible_check()
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, "-v", "--no-paging"])
    assert result.exit_code == 0
    assert check.identifier in result.output


def test_describe_check_relative_id(cli_runner: CliRunner):
    """Resolving a check by '<req#>.<check#>' renders the single-check view."""
    _, requirement, check = _first_visible_check()
    relative = f"{requirement.order_number}.{check.order_number}"
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, relative, "--no-paging"])
    assert result.exit_code == 0, result.output
    assert check.identifier in result.output
    assert check.severity.name in result.output


def test_describe_check_full_id(cli_runner: CliRunner):
    """Resolving a check by full '<profile>_<req#>.<check#>'."""
    _, _, check = _first_visible_check()
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, check.identifier, "--no-paging"])
    assert result.exit_code == 0, result.output
    assert check.identifier in result.output


def test_describe_check_unknown(cli_runner: CliRunner):
    """An out-of-range check id produces a usage error with a hint."""
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, "99.99", "--no-paging"])
    assert result.exit_code == 2
    assert "No requirement #99" in result.output


def test_describe_check_bad_format(cli_runner: CliRunner):
    """A non-numeric check id is rejected with a format hint."""
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, "not-an-id", "--no-paging"])
    assert result.exit_code == 2
    assert "Invalid check identifier" in result.output


def test_describe_check_profile_mismatch(cli_runner: CliRunner):
    """A full id whose prefix doesn't match the requested profile is rejected."""
    result = cli_runner.invoke(
        cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, "some-other-profile_1.1", "--no-paging"]
    )
    assert result.exit_code == 2
    assert "does not belong to profile" in result.output


def test_describe_check_verbose_python(cli_runner: CliRunner):
    """Verbose single-check view on a Python-backed check shows the function source."""
    _, requirement, check = _first_visible_check()
    relative = f"{requirement.order_number}.{check.order_number}"
    result = cli_runner.invoke(
        cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, relative, "-v", "--no-paging"]
    )
    assert result.exit_code == 0, result.output
    assert "Source" in result.output
    # The decorated check function is what gets serialized
    assert "@check" in result.output


def test_describe_check_verbose_shacl(cli_runner: CliRunner):
    """Verbose single-check view on a SHACL-backed check shows turtle source."""
    _, requirement, check = _first_shacl_check()
    relative = f"{requirement.order_number}.{check.order_number}"
    result = cli_runner.invoke(
        cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, relative, "-v", "--no-paging"]
    )
    assert result.exit_code == 0, result.output
    assert "Source" in result.output
    # SHACL serialized as turtle should contain a sh: prefix and a NodeShape/PropertyShape declaration
    assert "sh:" in result.output


def test_describe_check_verbose_shacl_includes_target(cli_runner: CliRunner):
    """For nested PropertyShape checks, the snippet must include the owning NodeShape's target."""
    profile = services.get_profile(_DESCRIBE_TEST_PROFILE)
    nested = None
    for requirement in profile.requirements:
        if requirement.hidden:
            continue
        for check in requirement.get_checks():
            if isinstance(check, SHACLCheck) and getattr(check._shape, "parent", None) is not None:
                nested = (requirement, check)
                break
        if nested:
            break
    if nested is None:
        # No nested PropertyShape check available in this profile; nothing to assert here.
        return
    requirement, check = nested
    relative = f"{requirement.order_number}.{check.order_number}"
    result = cli_runner.invoke(
        cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, relative, "-v", "--no-paging"]
    )
    assert result.exit_code == 0, result.output
    # The snippet must surface the owning shape's target declaration so the user can see
    # what the property check applies to.
    assert any(t in result.output for t in ("sh:targetClass", "sh:targetNode",
                                            "sh:targetSubjectsOf", "sh:targetObjectsOf",
                                            "sh:target "))
