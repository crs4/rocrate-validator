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

import json
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from pytest import fixture, mark

from rocrate_validator import services
from rocrate_validator.cli.main import cli
from rocrate_validator.models import BatchCrateEntry, BatchSession, ValidationSettings
from rocrate_validator.requirements.python import PyFunctionCheck
from rocrate_validator.requirements.shacl.checks import SHACLCheck
from rocrate_validator.services import discover_ro_crates
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.paths import get_user_sessions_dir
from rocrate_validator.utils.versioning import get_version
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import CRATES_DATA_PATH, InvalidFileDescriptor, ValidROC

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
    result = cli_runner.invoke(
        cli,
        ["validate", str(InvalidFileDescriptor().invalid_json_format), "--verbose", "--no-paging", "-p", "ro-crate"],
    )
    logger.error(result.output)
    assert result.exit_code == 1


def test_validate_subcmd_valid_local_folder_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["validate", str(ValidROC().wrroc_paper_long_date), "--verbose", "--no-paging"])
    assert result.exit_code == 0
    assert re.search(r"RO-Crate.*is a valid", result.output)


def test_validate_subcmd_valid_remote_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(
        cli,
        [
            "validate",
            str(ValidROC().sort_and_change_remote),
            "--verbose",
            "--no-paging",
            "--skip-checks",
            SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
        ],
    )
    assert result.exit_code == 0
    assert re.search(r"RO-Crate.*is a valid", result.output)


def test_validate_subcmd_invalid_local_archive_rocrate(cli_runner: CliRunner):
    result = cli_runner.invoke(
        cli,
        [
            "validate",
            str(ValidROC().sort_and_change_archive),
            "--verbose",
            "--no-paging",
            "--skip-checks",
            SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
        ],
    )
    assert result.exit_code == 0
    assert re.search(r"RO-Crate.*is a valid", result.output)


def test_validate_skip_checks_option(cli_runner: CliRunner):
    # Patch the validation service to capture the skip_checks argument
    called_args: list = []
    called_kwargs: dict = {}

    def mock_validate(*args, **kwargs):
        logger.warning(f"Mock validate called with args: {args}, kwargs: {kwargs}")

        called_args.extend(args)
        called_kwargs.update(kwargs)

        logger.debug(f"Args: {args}")
        logger.debug(f"Kwargs: {kwargs}")
        logger.debug(f"Called args: {called_args}")
        logger.debug(f"Called kwargs: {called_kwargs}")

    with patch("rocrate_validator.cli.commands.validate.services.validate") as mock_validate_rocrate:
        mock_validate_rocrate.return_value = None
        mock_validate_rocrate.side_effect = mock_validate

        skip_checks_1 = ("a", "b", "c")
        skip_checks_2 = ("d", "e", "f")
        result = cli_runner.invoke(
            cli,
            [
                "--no-interactive",
                "validate",
                str(ValidROC().sort_and_change_remote),
                "--skip-checks",
                ",".join(skip_checks_1),
                "--skip-checks",
                ",".join(skip_checks_2),
                "--no-paging",
            ],
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
        assert list(skip_checks_1 + skip_checks_2) == settings["skip_checks"], (
            f"Expected skip_checks to be {list(skip_checks_1 + skip_checks_2)}, but got {settings['skip_checks']}"
        )


def test_validate_output_file_text_report(cli_runner: CliRunner, tmp_path: Path):
    output_file = tmp_path / "report.txt"
    result = cli_runner.invoke(
        cli,
        [
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--verbose",
            "--no-paging",
            "-o",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "AttributeError" not in result.output
    assert output_file.exists(), "The text report file was not created"
    assert output_file.read_text(encoding="utf-8").strip(), "The text report file is empty"


def test_validate_output_file_json_report(cli_runner: CliRunner, tmp_path: Path):
    output_file = tmp_path / "report.json"
    result = cli_runner.invoke(
        cli,
        [
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--no-paging",
            "--output-format",
            "json",
            "-w",
            "10000",
            "-o",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "AttributeError" not in result.output
    assert output_file.exists(), "The JSON report file was not created"
    json.loads(output_file.read_text(encoding="utf-8"))  # must be valid JSON


def test_validate_with_invalid_profiles_path_dir(cli_runner: CliRunner):
    dummy_profiles_path = "/tmp/dummy_profiles"
    result = cli_runner.invoke(
        cli,
        [
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--profiles-path",
            dummy_profiles_path,
            "--verbose",
            "--no-paging",
        ],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 2
    # On narrow terminals the Rich error panel wraps the message across lines
    # and inserts box-drawing borders (│) between words; strip those and
    # collapse whitespace so the match does not depend on terminal width.
    normalized_output = re.sub(r"[\s│]+", " ", result.output)
    assert re.search(f"Path '{dummy_profiles_path}' does not exist.", normalized_output)


def test_profiles_list(cli_runner: CliRunner):
    """
    Test the list of profiles.
    """
    result = cli_runner.invoke(cli, ["profiles", "list", "--no-paging"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "ro-crate-1.1" in result.output  # Check for a known profile


def test_extra_profiles_list(cli_runner: CliRunner, fake_profiles_path: Path):
    """
    Test the list of extra profiles.
    """
    result = cli_runner.invoke(
        cli,
        ["profiles", "--extra-profiles-path", str(fake_profiles_path), "list", "--no-paging"],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0
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
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, relative, "-v", "--no-paging"])
    assert result.exit_code == 0, result.output
    assert "Source" in result.output
    # The decorated check function is what gets serialized
    assert "@check" in result.output


def test_describe_check_verbose_shacl(cli_runner: CliRunner):
    """Verbose single-check view on a SHACL-backed check shows turtle source."""
    _, requirement, check = _first_shacl_check()
    relative = f"{requirement.order_number}.{check.order_number}"
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, relative, "-v", "--no-paging"])
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
    result = cli_runner.invoke(cli, ["profiles", "describe", _DESCRIBE_TEST_PROFILE, relative, "-v", "--no-paging"])
    assert result.exit_code == 0, result.output
    # The snippet must surface the owning shape's target declaration so the user can see
    # what the property check applies to.
    assert any(
        t in result.output
        for t in ("sh:targetClass", "sh:targetNode", "sh:targetSubjectsOf", "sh:targetObjectsOf", "sh:target ")
    )


###############################################################################
# BATCH MODE TESTS
###############################################################################


def test_discover_ro_crates_directory():
    """Test discover_ro_crates finds crates in a directory."""
    valid_path = CRATES_DATA_PATH / "valid"
    crates = discover_ro_crates(valid_path)
    assert len(crates) > 0
    # Should find subdirectories with ro-crate-metadata.json
    assert any("wrroc-paper-long-date" in str(c) for c in crates)
    assert any("wrroc-paper" in str(c) for c in crates)
    # Should find .zip files
    assert any(c.suffix == ".zip" for c in crates)


def test_discover_ro_crates_no_match_pattern():
    """Test discover_ro_crates with a pattern that matches nothing."""
    valid_path = CRATES_DATA_PATH / "valid"
    crates = discover_ro_crates(valid_path, pattern="nonexistent*.zip")
    assert len(crates) == 0


def test_discover_ro_crates_is_flat(tmp_path):
    """Discovery is flat: a crate's nested payload is not treated as a separate crate."""
    crate = tmp_path / "crateB"
    (crate / "data").mkdir(parents=True)
    (crate / "ro-crate-metadata.json").write_text("{}")
    # A nested metadata file is a payload of crateB and must NOT be discovered.
    (crate / "data" / "ro-crate-metadata.json").write_text("{}")

    crates = discover_ro_crates(tmp_path)
    assert any(c.name == "crateB" for c in crates)
    assert all(c.resolve() != (crate / "data").resolve() for c in crates)


def test_discover_ro_crates_detached_metadata_files(tmp_path):
    """Detached crates defined as immediate `*-ro-crate-metadata.json` files are found."""
    # Two detached crates (metadata files directly in the scan dir).
    (tmp_path / "crate_0001-ro-crate-metadata.json").write_text("{}")
    (tmp_path / "crate_0002-ro-crate-metadata.json").write_text("{}")
    # A directory crate alongside them.
    dir_crate = tmp_path / "crate_0003"
    dir_crate.mkdir()
    (dir_crate / "ro-crate-metadata.json").write_text("{}")
    # Non-crate files must be ignored.
    (tmp_path / "generation_report.json").write_text("{}")
    (tmp_path / ".DS_Store").write_text("")

    crates = discover_ro_crates(tmp_path)
    names = {c.name for c in crates}
    assert "crate_0001-ro-crate-metadata.json" in names
    assert "crate_0002-ro-crate-metadata.json" in names
    assert "crate_0003" in names
    assert "generation_report.json" not in names
    assert ".DS_Store" not in names
    assert len(crates) == 3


def test_discover_ro_crates_self_as_crate():
    """Test that a directory with ro-crate-metadata.json is found as a crate."""
    crate_dir = ValidROC().wrroc_paper_long_date
    crates = discover_ro_crates(crate_dir)
    assert len(crates) >= 1
    assert crate_dir.resolve() in crates


def test_discover_ro_crates_invalid_dir():
    """Test discover_ro_crates raises on non-directory."""
    with tempfile.NamedTemporaryFile() as tmp:
        import pytest

        with pytest.raises(NotADirectoryError):
            discover_ro_crates(Path(tmp.name))


def test_batch_crate_entry_serialization():
    """Test BatchCrateEntry to_dict/from_dict roundtrip."""
    entry = BatchCrateEntry(
        path="/tmp/test-crate",
        status="completed",
        passed=True,
        duration=1.23,
        issues=[{"message": "test issue"}],
        statistics={"total_checks": 10},
    )
    data = entry.to_dict()
    restored = BatchCrateEntry.from_dict(data)
    assert restored.path == entry.path
    assert restored.status == entry.status
    assert restored.passed == entry.passed
    assert restored.duration == entry.duration
    assert restored.issues == entry.issues
    assert restored.statistics == entry.statistics


def test_batch_session_save_load(tmp_path):
    """Test BatchSession save/load roundtrip."""
    settings = {"profile_identifier": "ro-crate", "requirement_severity": "REQUIRED"}
    session = BatchSession(
        validation_settings=settings,
        crate_paths=["/tmp/crate1", "/tmp/crate2"],
        session_path=tmp_path / "session.json",
    )
    assert session.total_crates == 2
    assert session.completed_crates == 0

    # Simulate a completed crate
    session.completed_crates = 1
    session.failed_crates = 0
    session.crates[0].status = "completed"
    session.crates[0].passed = True
    session.save()

    # Load it back
    loaded = BatchSession.load(tmp_path / "session.json")
    assert loaded.total_crates == 2
    assert loaded.completed_crates == 1
    assert loaded.validation_settings["profile_identifier"] == "ro-crate"
    assert loaded.crates[0].status == "completed"
    assert loaded.crates[0].passed is True
    assert loaded.crates[1].status == "pending"


def test_batch_session_get_pending():
    """Test get_pending returns only pending/in_progress entries."""
    session = BatchSession(
        validation_settings={},
        crate_paths=["/tmp/a", "/tmp/b", "/tmp/c"],
    )
    session.crates[0].status = "completed"
    session.crates[1].status = "in_progress"
    pending = session.get_pending()
    assert len(pending) == 2
    assert pending[0].path == "/tmp/b"
    assert pending[1].path == "/tmp/c"


def test_batch_session_is_completed():
    """Test is_completed returns True only when all crates done."""
    session = BatchSession(validation_settings={}, crate_paths=["/tmp/a"])
    assert not session.is_completed()
    session.completed_crates = 1
    assert session.is_completed()


def test_batch_session_mark_failed():
    """Test mark_failed updates session state correctly."""
    session = BatchSession(validation_settings={}, crate_paths=["/tmp/a"])
    session.mark_failed("/tmp/a", "Connection error", 0.5)
    assert session.crates[0].status == "failed"
    assert session.crates[0].passed is False
    assert session.crates[0].error == "Connection error"
    assert session.completed_crates == 1
    assert session.failed_crates == 1


def test_batch_validate_valid_crates(cli_runner: CliRunner):
    """Test batch validation of valid crates via CLI."""
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper*",
            # The wrroc-paper crates declare RO-Crate 1.1: validate against the
            # matching version (the bare "ro-crate" now resolves to the newest
            # available profile, 1.2, against which these 1.1 crates fail).
            "--profile-identifier",
            "ro-crate-1.1",
            "--verbose",
            "--no-paging",
        ],
    )
    # Should succeed with at least 2 valid crates found
    assert result.exit_code == 0, result.output
    assert "Batch Validation Summary" in result.output


def test_batch_validate_auto_session(cli_runner: CliRunner):
    """Batch validation auto-manages a session file under the user sessions dir."""
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper-long-date",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            # No --session-file / --resume: the session is always auto-managed.
            "--no-resume",
        ],
    )
    assert result.exit_code == 0, result.output
    # A session file must have been auto-created under the user sessions directory.
    sessions = list(get_user_sessions_dir().glob("*.json"))
    assert sessions, "no auto-managed session file was created"
    session_data = json.loads(max(sessions, key=lambda p: p.stat().st_mtime).read_text())
    assert session_data["session"]["status"] == "completed"
    assert session_data["session"]["completed_crates"] >= 1
    assert session_data["crates"][0]["status"] == "completed"
    # The profile used is recorded per crate in the session.
    assert session_data["crates"][0]["profiles"] == ["ro-crate-1.1"]


def test_batch_validate_json_output(cli_runner: CliRunner, tmp_path):
    """Test batch validation with JSON output file."""
    output_file = tmp_path / "batch_output.json"
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper-long-date",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            "--output-format",
            "json",
            "--output-file",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_file.exists()
    # Use strict=False to handle any embedded control characters in validation messages
    data = json.loads(output_file.read_text(), strict=False)
    assert "meta" in data
    assert "batch_passed" in data


def test_batch_validate_mixed_crates(cli_runner: CliRunner, tmp_path):
    """Test batch validation with mix of valid and invalid crates."""
    # Create temp dir with both valid and invalid crates
    batch_dir = tmp_path / "batch_mixed"
    batch_dir.mkdir()
    valid_src = ValidROC().wrroc_paper_long_date
    invalid_src = InvalidFileDescriptor().invalid_json_format

    # Copy valid crate
    import shutil

    shutil.copytree(valid_src, batch_dir / "valid_crate", symlinks=True)
    # Copy invalid crate
    shutil.copytree(invalid_src, batch_dir / "invalid_crate", symlinks=True)

    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            str(batch_dir),
            "--profile-identifier",
            "ro-crate",
            "--no-paging",
            "--verbose",
        ],
    )
    # Should fail because at least one crate fails
    assert result.exit_code == 1, result.output
    assert "Batch Validation Summary" in result.output
    # Verbose per-crate details are rendered (from the session entries)
    assert "Failed crate details:" in result.output


def test_batch_verbose_details_rendered_from_session_entries():
    """
    Verbose failed-crate details must come from the persisted session entries:
    no live ValidationResult is retained by a batch run (their contexts would
    pin every crate's graphs in memory for the whole batch).
    """
    import io

    from rocrate_validator.cli.ui.text.validate import BatchValidationCommandView
    from rocrate_validator.models import BatchValidationResult
    from rocrate_validator.utils.io_helpers.output.console import Console

    session = BatchSession(validation_settings={}, crate_paths=["/tmp/crate_x", "/tmp/crate_y"])
    failed = session.crates[0]
    failed.status = "completed"
    failed.passed = False
    failed.duration = 1.2
    failed.statistics = {"total_checks": 3, "total_passed_checks": 2, "total_failed_checks": 1}
    failed.issues = [
        {
            "severity": "REQUIRED",
            "message": "The root entity is missing",
            "check": {"identifier": "ro-crate-1.1_1.1", "name": "Root entity existence"},
        }
    ]
    errored = session.crates[1]
    errored.status = "failed"
    errored.passed = False
    errored.error = "RO-Crate metadata not found"
    session.completed_crates = 2
    session.failed_crates = 2

    out = Console(file=io.StringIO(), width=200, color_system=None)
    BatchValidationCommandView(console=out).show_summary(BatchValidationResult(session), verbose=True)
    rendered = out.file.getvalue()

    assert "Failed crate details:" in rendered
    assert "ro-crate-1.1_1.1" in rendered
    assert "The root entity is missing" in rendered
    # Entries that errored out (no check breakdown) show their error message
    assert "RO-Crate metadata not found" in rendered


def test_batch_validate_keep_results(tmp_path):
    """Live results are dropped by default and retained only with keep_results=True."""
    crate = str(ValidROC().wrroc_paper_long_date)
    settings = ValidationSettings.parse({"profile_identifier": ("ro-crate",)})

    dropped = services.batch_validate(
        settings,
        [crate],
        session_path=tmp_path / "dropped.json",
        profile_identifiers=["ro-crate"],
        no_auto_profile=True,
    )
    assert dropped.live_results == [], "live results must not be retained by default"
    assert dropped.total_crates() == 1, "the session outcome is recorded regardless"

    kept = services.batch_validate(
        settings,
        [crate],
        session_path=tmp_path / "kept.json",
        profile_identifiers=["ro-crate"],
        no_auto_profile=True,
        keep_results=True,
    )
    assert [path for path, _ in kept.live_results] == [crate]
    assert all(hasattr(result, "passed") for _, result in kept.live_results)


def test_batch_prepare_session_auto_resume(tmp_path):
    """An interrupted session is auto-resumed: completed crates are carried over."""
    session_file = tmp_path / "auto_session.json"
    paths = ["/tmp/crate_a", "/tmp/crate_b", "/tmp/crate_c"]

    # Simulate a previously interrupted session with one completed crate.
    session = BatchSession(validation_settings={}, crate_paths=paths, session_path=session_file)
    session.crates[0].status = "completed"
    session.crates[0].passed = True
    session.completed_crates = 1
    session.status = "interrupted"
    session.save()

    settings = ValidationSettings.parse({"profile_identifier": ("ro-crate",)})

    # Resume (fresh=False): the completed crate is skipped, the rest are pending.
    resumed, pending = services._prepare_batch_session(settings, paths, session_file, fresh=False)
    assert resumed.completed_crates == 1
    assert resumed.total_crates == 3
    assert set(pending) == {"/tmp/crate_b", "/tmp/crate_c"}

    # Fresh (fresh=True): everything is re-validated, nothing carried over.
    restarted, pending_fresh = services._prepare_batch_session(settings, paths, session_file, fresh=True)
    assert restarted.completed_crates == 0
    assert set(pending_fresh) == set(paths)


def test_batch_session_path_reflects_profile_selection(tmp_path):
    """The session key must distinguish profile selections, order-independently."""
    settings = ValidationSettings.parse(
        {"rocrate_uri": ".", "profile_identifier": "ro-crate", "requirement_severity": "REQUIRED"}
    )

    def sp(profile_identifiers, no_auto_profile=False, severity_only=False):
        s = ValidationSettings.parse(
            {
                "rocrate_uri": ".",
                "profile_identifier": "ro-crate",
                "requirement_severity": "REQUIRED",
                "requirement_severity_only": severity_only,
            }
        )
        return services.resolve_batch_session_path(
            s, tmp_path, "*", profile_identifiers=profile_identifiers, no_auto_profile=no_auto_profile
        )

    # Different multi-profile sets sharing the first profile must NOT collide.
    assert sp(["ro-crate-1.1", "ro-crate-1.2"]) != sp(["ro-crate-1.1", "ro-crate-process-run"])
    # Profile order does not matter.
    assert sp(["ro-crate-1.1", "ro-crate-1.2"]) == sp(["ro-crate-1.2", "ro-crate-1.1"])
    # Auto-detection, disabled auto-detection and an explicit profile are all distinct.
    assert sp(None, no_auto_profile=False) != sp(None, no_auto_profile=True)
    assert sp(["ro-crate-1.1"]) != sp(None, no_auto_profile=False)
    # requirement_severity_only changes the key (it is dropped by to_dict()).
    assert sp(["ro-crate-1.1"], severity_only=False) != sp(["ro-crate-1.1"], severity_only=True)

    # Sanity: a stable selection resolves to a stable path.
    assert services.resolve_batch_session_path(
        settings, tmp_path, "*", profile_identifiers=["ro-crate-1.1"]
    ) == services.resolve_batch_session_path(settings, tmp_path, "*", profile_identifiers=["ro-crate-1.1"])


def test_batch_footer_reports_saved_paths(cli_runner: CliRunner, tmp_path):
    """The end-of-batch footer reports where the report file and session were saved."""
    output_file = tmp_path / "report.txt"
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper-long-date",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            "--output-format",
            "text",
            "--output-file",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
    # The footer (on stderr) names the saved artifacts and the input scanned.
    assert "Report (text)" in result.stderr
    assert str(output_file) in result.stderr
    assert "Session" in result.stderr
    assert ".json" in result.stderr
    assert "Input" in result.stderr
    # Per-crate progress lines show the crate relative to the input path
    # (the bare crate name, not an absolute path).
    assert "] wrroc-paper-long-date" in result.stderr


def test_batch_validate_csv_output(cli_runner: CliRunner, tmp_path):
    """Test batch validation with CSV output file."""
    output_file = tmp_path / "batch_output.csv"
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper-long-date",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            "--output-format",
            "csv",
            "--output-file",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_file.exists()
    rows = output_file.read_text().splitlines()
    assert rows[0].startswith(
        "source,crate,path,profiles,size_bytes,status,total_checks,passed_checks,issues,duration,error"
    )
    # The profile used is recorded in the CSV row.
    assert ",ro-crate-1.1," in rows[1]
    # At least one data row for the validated crate, reported as passed.
    assert len(rows) >= 2
    assert "wrroc-paper-long-date" in rows[1]
    assert ",passed," in rows[1]


def test_batch_validate_csv_rejected_in_single_mode(cli_runner: CliRunner):
    """CSV output is batch-only and must be rejected for single-crate validation."""
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--profile-identifier",
            "ro-crate",
            "--no-paging",
            "--output-format",
            "csv",
        ],
    )
    assert result.exit_code != 0
    assert "csv" in result.output.lower()


def test_batch_validate_no_crates_found(cli_runner: CliRunner, tmp_path):
    """Test batch with no matching crates."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            str(empty_dir),
            "--no-paging",
        ],
    )
    assert result.exit_code == 0
    assert "No RO-Crates found" in result.output


def test_batch_with_output_file_text(cli_runner: CliRunner, tmp_path):
    """Test batch validation writes text output to file."""
    output_file = tmp_path / "batch_report.txt"
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper-long-date",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            "--output-format",
            "text",
            "--output-file",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_file.exists()
    content = output_file.read_text()
    assert "Batch Validation Summary" in content


def test_batch_canonical_positional_target(cli_runner: CliRunner):
    """The scan root can be given as the positional RO-CRATE-URI argument (no -B)."""
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper*",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Batch Validation Summary" in result.output


def test_no_resume_ignores_saved_session(cli_runner: CliRunner):
    """--no-resume re-validates from scratch instead of resuming a saved session."""
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper-long-date",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            "--no-resume",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Batch Validation Summary" in result.output


@mark.parametrize("flag", ["--batch-pattern=foo*", "--no-resume"])
def test_batch_only_options_require_batch_mode(cli_runner: CliRunner, flag: str):
    """Batch-only options must be rejected when batch mode is not enabled."""
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            *flag.split("="),
        ],
    )
    assert result.exit_code != 0
    assert "batch mode" in result.output.lower()


def _write_fake_session(sessions_dir, session_id, *, status, total, completed, failed, paths):
    """Create a minimal batch session file under ``sessions_dir`` for tests."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    now = "2026-06-22T10:00:00+00:00"
    data = {
        "session": {
            "version": "1.0",
            "rocrate_validator_version": "test",
            "created_at": now,
            "updated_at": now,
            "status": status,
            "total_crates": total,
            "completed_crates": completed,
            "failed_crates": failed,
        },
        "validation_settings": {},
        "batch_options": {"profile_identifiers": ["ro-crate-1.1"], "no_auto_profile": False},
        "crates": [
            {
                "path": p,
                "status": "completed",
                "passed": True,
                "profiles": ["ro-crate-1.1"],
                "issues": [],
                "statistics": {"total_checks": 1, "total_passed_checks": 1},
            }
            for p in paths
        ],
    }
    (sessions_dir / f"{session_id}.json").write_text(json.dumps(data), encoding="utf-8")


@fixture
def isolated_sessions_dir(tmp_path, monkeypatch):
    """Redirect the user cache dir to a tmp path so session tests stay isolated."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return get_user_sessions_dir()


def test_sessions_path(cli_runner: CliRunner, isolated_sessions_dir):
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "path"])
    assert result.exit_code == 0, result.output
    assert str(isolated_sessions_dir) in result.output


def test_sessions_show_requires_id_non_interactive(cli_runner: CliRunner, isolated_sessions_dir):
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "show"])
    assert result.exit_code != 0
    assert "specify a session id" in result.output.lower()


def test_sessions_show_not_found(cli_runner: CliRunner, isolated_sessions_dir):
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "show", "nope404"])
    assert result.exit_code == 0, result.output
    assert "no session matches" in result.output.lower()


def test_validate_stats_text(cli_runner: CliRunner):
    """`validate -b --stats` appends the textual statistics after the summary."""
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper*",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            "--no-resume",
            "--stats",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Statistics" in result.output
    assert "Outcome Summary" in result.output


def test_validate_stats_ignored_for_json(cli_runner: CliRunner, tmp_path):
    """--stats is ignored for JSON output (text-only): the report file stays valid JSON."""
    output_file = tmp_path / "out.json"
    valid_dir = str(ValidROC().wrroc_paper_long_date.parent)
    result = cli_runner.invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            "--batch",
            valid_dir,
            "--batch-pattern",
            "wrroc-paper-long-date",
            "--profile-identifier",
            "ro-crate-1.1",
            "--no-paging",
            "--no-resume",
            "--output-format",
            "json",
            "--output-file",
            str(output_file),
            "--stats",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "ignored for 'json'" in result.stderr
    # The report file is plain JSON, with no statistics tables mixed in.
    data = json.loads(output_file.read_text(), strict=False)
    assert "batch_passed" in data


def test_sessions_show_stats(cli_runner: CliRunner, isolated_sessions_dir):
    _write_fake_session(
        isolated_sessions_dir,
        "stat01",
        status="completed",
        total=2,
        completed=2,
        failed=0,
        paths=["/data/crateA", "/data/crateB"],
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "show", "stat01", "--stats"])
    assert result.exit_code == 0, result.output
    assert "Statistics" in result.output
    assert "Outcome Summary" in result.output


def test_sessions_show_output_file_requires_stats(cli_runner: CliRunner, isolated_sessions_dir):
    """--output-file without --stats should raise a usage error."""
    _write_fake_session(
        isolated_sessions_dir,
        "s1",
        status="completed",
        total=1,
        completed=1,
        failed=0,
        paths=["/a/x"],
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "show", "s1", "-o", "/tmp/out.txt"])
    assert result.exit_code != 0
    assert "requires --stats" in result.output


def test_sessions_show_stats_output_file_text(cli_runner: CliRunner, isolated_sessions_dir, tmp_path):
    """Write statistics in text format (default, no colour) to a file."""
    output_file = tmp_path / "stats.txt"
    _write_fake_session(
        isolated_sessions_dir,
        "s1",
        status="completed",
        total=2,
        completed=2,
        failed=0,
        paths=["/a/x", "/a/y"],
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "show", "s1", "--stats", "-o", str(output_file)])
    assert result.exit_code == 0, result.output
    assert "Statistics written to" in result.output
    content = output_file.read_text()
    assert "Statistics" in content
    assert "Outcome Summary" in content
    # No ANSI colour codes in default text output.
    assert "\x1b[" not in content


def test_sessions_show_stats_output_file_text_with_color(cli_runner: CliRunner, isolated_sessions_dir, tmp_path):
    """Write statistics in text format with ANSI colour codes."""
    output_file = tmp_path / "stats_color.txt"
    _write_fake_session(
        isolated_sessions_dir,
        "s1",
        status="completed",
        total=2,
        completed=2,
        failed=0,
        paths=["/a/x", "/a/y"],
    )
    result = cli_runner.invoke(
        cli, ["--no-interactive", "sessions", "show", "s1", "--stats", "-o", str(output_file), "--color"]
    )
    assert result.exit_code == 0, result.output
    content = output_file.read_text()
    assert "Statistics" in content
    assert "Outcome Summary" in content
    assert "\x1b[" in content


def test_sessions_show_stats_output_file_md(cli_runner: CliRunner, isolated_sessions_dir, tmp_path):
    """Write statistics in markdown format to a file."""
    output_file = tmp_path / "stats.md"
    _write_fake_session(
        isolated_sessions_dir,
        "s1",
        status="completed",
        total=2,
        completed=2,
        failed=0,
        paths=["/a/x", "/a/y"],
    )
    result = cli_runner.invoke(
        cli, ["--no-interactive", "sessions", "show", "s1", "--stats", "-o", str(output_file), "-f", "md"]
    )
    assert result.exit_code == 0, result.output
    content = output_file.read_text()
    assert "# Validation Statistics" in content
    assert "## Outcome Summary" in content
    assert "| Status | Crates | Share |" in content
    assert "| **TOTAL**" in content
    assert "## Checks/Passed Combinations" in content


def test_sessions_show_stats_output_file_md_with_failures(cli_runner: CliRunner, isolated_sessions_dir, tmp_path):
    """Write statistics in markdown format for a session with failures."""
    output_file = tmp_path / "stats_fail.md"
    sessions_dir = isolated_sessions_dir
    sessions_dir.mkdir(parents=True, exist_ok=True)
    now = "2026-06-22T10:00:00+00:00"
    data = {
        "session": {
            "version": "1.0",
            "rocrate_validator_version": "test",
            "created_at": now,
            "updated_at": now,
            "status": "completed",
            "total_crates": 4,
            "completed_crates": 4,
            "failed_crates": 2,
        },
        "validation_settings": {},
        "batch_options": {"profile_identifiers": ["ro-crate-1.1"], "no_auto_profile": False},
        "crates": [
            {
                "path": "/a/passed1",
                "status": "completed",
                "passed": True,
                "profiles": ["ro-crate-1.1"],
                "issues": [],
                "statistics": {"total_checks": 5, "total_passed_checks": 5},
            },
            {
                "path": "/a/passed2",
                "status": "completed",
                "passed": True,
                "profiles": ["ro-crate-1.1"],
                "issues": [],
                "statistics": {"total_checks": 5, "total_passed_checks": 5},
            },
            {
                "path": "/a/failed1",
                "status": "completed",
                "passed": False,
                "profiles": ["ro-crate-1.1"],
                "issues": [
                    {
                        "severity": "REQUIRED",
                        "check": {"identifier": "check-01", "name": "Check Alpha"},
                    },
                    {
                        "severity": "OPTIONAL",
                        "check": {"identifier": "check-02", "name": "Check Beta"},
                    },
                ],
                "statistics": {"total_checks": 5, "total_passed_checks": 3},
            },
            {
                "path": "/a/failed2",
                "status": "completed",
                "passed": False,
                "profiles": ["ro-crate-1.1"],
                "issues": [
                    {
                        "severity": "REQUIRED",
                        "check": {"identifier": "check-01", "name": "Check Alpha"},
                    },
                ],
                "statistics": {"total_checks": 5, "total_passed_checks": 4},
            },
        ],
    }
    (sessions_dir / "s1.json").write_text(json.dumps(data), encoding="utf-8")

    result = cli_runner.invoke(
        cli, ["--no-interactive", "sessions", "show", "s1", "--stats", "-o", str(output_file), "-f", "md"]
    )
    assert result.exit_code == 0, result.output
    content = output_file.read_text()
    assert "Crates analysed: **4**" in content
    assert "| PASSED | 2 | 50.0% |" in content
    assert "| FAILED | 2 | 50.0% |" in content
    assert "## Error-Type Distribution" in content
    assert "## Issue Attribution" in content


def test_sessions_show_renders_session(cli_runner: CliRunner, isolated_sessions_dir):
    _write_fake_session(
        isolated_sessions_dir,
        "sess001",
        status="completed",
        total=2,
        completed=2,
        failed=0,
        paths=["/data/crateA", "/data/crateB"],
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "show", "sess001"])
    assert result.exit_code == 0, result.output
    out = result.output
    # Header, per-crate list (relative names + profile) and summary are all shown.
    assert "Profiles" in out
    assert "crateA" in out and "crateB" in out
    assert "ro-crate-1.1" in out
    assert "Batch Validation Summary" in out
    assert "passed validation" in out.lower()


def test_sessions_list_empty(cli_runner: CliRunner, isolated_sessions_dir):
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "list"])
    assert result.exit_code == 0, result.output
    assert "no batch sessions" in result.output.lower()


def test_sessions_list_and_json(cli_runner: CliRunner, isolated_sessions_dir):
    _write_fake_session(
        isolated_sessions_dir, "aaa111", status="completed", total=2, completed=2, failed=0, paths=["/a/x", "/a/y"]
    )
    _write_fake_session(
        isolated_sessions_dir, "bbb222", status="interrupted", total=3, completed=1, failed=1, paths=["/b/x"]
    )

    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "list"])
    assert result.exit_code == 0, result.output
    assert "Batch sessions (2)" in result.output

    result_json = cli_runner.invoke(cli, ["--no-interactive", "sessions", "ls", "--json"])
    assert result_json.exit_code == 0, result_json.output
    data = json.loads(result_json.output)
    assert {d["id"] for d in data} == {"aaa111", "bbb222"}

    filtered = cli_runner.invoke(cli, ["--no-interactive", "sessions", "list", "--status", "interrupted"])
    assert "Batch sessions (1)" in filtered.output


def test_sessions_clear_requires_scope(cli_runner: CliRunner, isolated_sessions_dir):
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "clear"])
    assert result.exit_code != 0
    assert "specify" in result.output.lower()


def test_sessions_clear_by_id(cli_runner: CliRunner, isolated_sessions_dir):
    _write_fake_session(
        isolated_sessions_dir, "abc123def", status="completed", total=1, completed=1, failed=0, paths=["/a/x"]
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "clear", "abc123", "--yes"])
    assert result.exit_code == 0, result.output
    assert "Removed 1 session" in result.output
    assert not (isolated_sessions_dir / "abc123def.json").exists()


def test_sessions_clear_completed_only(cli_runner: CliRunner, isolated_sessions_dir):
    _write_fake_session(
        isolated_sessions_dir, "done1", status="completed", total=1, completed=1, failed=0, paths=["/a/x"]
    )
    _write_fake_session(
        isolated_sessions_dir, "wip1", status="interrupted", total=2, completed=1, failed=0, paths=["/b/x"]
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "rm", "--completed", "--yes"])
    assert result.exit_code == 0, result.output
    assert not (isolated_sessions_dir / "done1.json").exists()
    assert (isolated_sessions_dir / "wip1.json").exists()


def test_sessions_clear_non_interactive_requires_yes(cli_runner: CliRunner, isolated_sessions_dir):
    _write_fake_session(
        isolated_sessions_dir, "keep1", status="completed", total=1, completed=1, failed=0, paths=["/a/x"]
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "clear", "--all"])
    assert result.exit_code == 1
    assert "--yes" in result.output
    # Nothing removed without confirmation.
    assert (isolated_sessions_dir / "keep1.json").exists()


def _make_interrupted_session(sessions_dir, session_id, crate_paths, completed_count, *, profile="ro-crate-1.1"):
    """Persist an interrupted batch session with the first crates marked completed."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"{session_id}.json"
    settings = ValidationSettings.parse(
        {"rocrate_uri": crate_paths[0], "profile_identifier": profile, "requirement_severity": "REQUIRED"}
    )
    session = BatchSession(
        validation_settings=settings.to_dict(),
        crate_paths=crate_paths,
        session_path=session_file,
    )
    for i in range(completed_count):
        session.crates[i].status = "completed"
        session.crates[i].passed = True
    session.completed_crates = completed_count
    session.status = "interrupted"
    session.profile_identifiers = [profile]
    session.save()
    return session_file


def test_sessions_resume_requires_id_non_interactive(cli_runner: CliRunner, isolated_sessions_dir):
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "resume"])
    assert result.exit_code != 0
    assert "specify a session id" in result.output.lower()


def test_sessions_resume_not_found(cli_runner: CliRunner, isolated_sessions_dir):
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "resume", "nope404"])
    assert result.exit_code == 0, result.output
    assert "no session matches" in result.output.lower()


def test_sessions_resume_already_completed(cli_runner: CliRunner, isolated_sessions_dir):
    _write_fake_session(
        isolated_sessions_dir, "done999", status="completed", total=1, completed=1, failed=0, paths=["/a/x"]
    )
    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "resume", "done999"])
    assert result.exit_code == 0, result.output
    assert "nothing to resume" in result.output.lower()


def test_sessions_resume_completes_interrupted(cli_runner: CliRunner, isolated_sessions_dir):
    valid_dir = ValidROC().wrroc_paper_long_date.parent
    c1 = str((valid_dir / "wrroc-paper").resolve())
    c2 = str((valid_dir / "wrroc-paper-long-date").resolve())
    session_file = _make_interrupted_session(isolated_sessions_dir, "feedface01", [c1, c2], completed_count=1)

    result = cli_runner.invoke(cli, ["--no-interactive", "sessions", "resume", "feedface"])
    assert result.exit_code == 0, result.output
    assert "passed validation" in result.output.lower()

    data = json.loads(session_file.read_text())
    assert data["session"]["status"] == "completed"
    assert data["session"]["completed_crates"] == 2
