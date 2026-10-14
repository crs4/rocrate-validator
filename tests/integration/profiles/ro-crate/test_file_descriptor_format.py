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
import logging
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from rocrate_validator import models, services
from rocrate_validator.cli.main import cli
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.utils.io_helpers.output.text.formatters import ValidationResultTextOutputFormatter
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import InvalidFileDescriptor, ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


# Global set up the paths
paths = InvalidFileDescriptor()


def _crate_with_suspicious_string_reference(tmp_path: Path, version: str) -> Path:
    source = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "crates"
        / f"rocrate-{version}"
        / "7_root_data_entity"
        / "recommended_reference_type_for_licence"
        / "valid"
    )
    crate = tmp_path / f"rocrate-{version}"
    shutil.copytree(source, crate)
    metadata_path = crate / "ro-crate-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    license_id = "https://creativecommons.org/licenses/by/4.0/"
    root = next(entity for entity in metadata["@graph"] if entity.get("@id") == "./")
    root["license"] = license_id
    root["customReference"] = license_id
    metadata["@context"] = [
        metadata["@context"],
        {"customReference": "https://example.org/vocabulary/customReference"},
    ]
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return crate


@pytest.mark.parametrize("version", ["1.2", "1.3"])
def test_diagnostic_checks_are_opt_in_and_non_blocking(tmp_path: Path, version: str):
    crate = _crate_with_suspicious_string_reference(tmp_path, version)
    settings = models.ValidationSettings(
        rocrate_uri=models.URI(crate),
        profile_identifier=f"ro-crate-{version}",
        requirement_severity=models.Severity.REQUIRED,
    )

    default_result = services.validate(settings)
    assert default_result.passed()
    assert default_result.diagnostics == []
    heuristic_check = next(
        check
        for check in default_result.statistics.diagnostic_checks
        if "suspicious entity references" in check.name.lower()
    )
    assert heuristic_check.severity == models.Severity.REQUIRED
    assert heuristic_check.diagnostic
    assert heuristic_check not in default_result.statistics.checks
    conformance_check_count = default_result.statistics.total_checks
    assert default_result.get_check_result(heuristic_check) is models.CheckResult.SKIPPED

    settings.include_diagnostic_checks = True
    diagnostic_result = services.validate(settings)
    assert diagnostic_result.passed()
    assert diagnostic_result.statistics.total_checks == conformance_check_count
    assert diagnostic_result.statistics.executed_diagnostic_checks == [heuristic_check]
    assert len(diagnostic_result.diagnostics) >= 2, (
        diagnostic_result.validation_settings.include_diagnostic_checks,
        [
            (check.name, diagnostic_result.get_check_result(check))
            for check in diagnostic_result.statistics.checks
            if "suspicious entity references" in check.name.lower()
        ],
        [detail.message for detail in diagnostic_result.skipped_check_details],
    )
    assert {diagnostic.violating_property for diagnostic in diagnostic_result.diagnostics} >= {
        "license",
        "customReference",
    }
    assert diagnostic_result.to_dict()["diagnostics"]

    console = Console(record=True, color_system=None, width=120)
    console.print(ValidationResultTextOutputFormatter(diagnostic_result))
    text_report = console.export_text()
    assert "Diagnostic Checks (1)" in text_report
    assert "customReference" in text_report

    cli_result = CliRunner().invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            str(crate),
            "--profile-identifier",
            f"ro-crate-{version}",
            "--include-diagnostic-checks",
            "--output-format",
            "json",
            "--no-paging",
        ],
    )
    assert cli_result.exit_code == 0, cli_result.output
    cli_report = json.loads(cli_result.output)
    assert cli_report["passed"]
    assert cli_report["diagnostics"]

    text_cli_result = CliRunner().invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            str(crate),
            "--profile-identifier",
            f"ro-crate-{version}",
            "--include-diagnostic-checks",
            "--no-paging",
        ],
    )
    assert text_cli_result.exit_code == 0, text_cli_result.output
    assert "Diagnostic Checks (1)" in text_cli_result.output
    assert "customReference" in text_cli_result.output

    skipped_result = CliRunner().invoke(
        cli,
        [
            "--no-interactive",
            "validate",
            str(crate),
            "--profile-identifier",
            f"ro-crate-{version}",
            "--include-diagnostic-checks",
            "--skip-checks",
            heuristic_check.identifier,
            "--output-format",
            "json",
            "--no-paging",
        ],
    )
    assert skipped_result.exit_code == 0, skipped_result.output
    skipped_report = json.loads(skipped_result.output)
    assert skipped_report["diagnostics"] == []


@pytest.mark.parametrize("version", ["1.2", "1.3"])
def test_required_about_reference_violation_is_detected_without_heuristic(tmp_path: Path, version: str):
    crate = _crate_with_suspicious_string_reference(tmp_path, version)
    metadata_path = crate / "ro-crate-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    descriptor = next(entity for entity in metadata["@graph"] if entity.get("@id") == "ro-crate-metadata.json")
    descriptor["about"] = {"@id": "./missing"}
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=models.URI(crate),
            profile_identifier=f"ro-crate-{version}",
            requirement_severity=models.Severity.REQUIRED,
        )
    )
    assert not result.passed()
    assert result.diagnostics == []


def test_missing_file_descriptor():
    """Test a RO-Crate without a file descriptor."""
    rocrate_path = paths.missing_file_descriptor
    do_entity_test(rocrate_path, models.Severity.REQUIRED, False, ["File Descriptor existence"], [])


def test_not_valid_json_format():
    """
    Test a RO-Crate with an invalid JSON file descriptor format.

    The validator must emit an ad-hoc issue reporting that the file descriptor is
    not valid JSON, including the position of the parsing error.
    """
    do_entity_test(
        paths.invalid_json_format,
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON format"],
        ['RO-Crate file descriptor "ro-crate-metadata.json" is not valid JSON'],
    )


def test_not_valid_json_format_aborts_validation():
    """
    An unparsable JSON file descriptor must abort the validation (fail-fast).

    Since the metadata cannot be read, no further check can run meaningfully, so the
    only reported failure must be the JSON-format one (no false positives).
    """
    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=models.URI(paths.invalid_json_format),
            requirement_severity=models.Severity.REQUIRED,
        )
    )
    assert not result.passed(), "An invalid-JSON crate must not pass validation"

    failed_requirements = [r.name for r in result.failed_requirements]
    assert failed_requirements == ["File Descriptor JSON format"], (
        f"Only the JSON-format requirement should fail, got: {failed_requirements}"
    )

    issues = [i.message for i in result.get_issues(models.Severity.REQUIRED) if i.message]
    assert len(issues) == 1, f"Exactly one issue expected, got: {issues}"
    assert "is not valid JSON" in issues[0]


def test_not_valid_jsonld_format_missing_context():
    """Test a RO-Crate with an invalid JSON-LD file descriptor format."""
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_context",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        [],
    )


def test_not_valid_jsonld_format_not_flattened():
    """Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor are not flattened.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/not_flattened",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ['RO-Crate file descriptor "ro-crate-metadata.json" is not fully flattened'],
    )


def test_not_valid_jsonld_format_not_valid_value_object():
    """Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor are not flattened.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/invalid_value_object",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        [
            'entity "nested-file.txt" contains both @id and @value',
            "is not a valid value object: @language and @type cannot coexist",
            'entity "invalidNestedReference" is not a valid node object reference',
            "entity \"{'@language': 'en', '@value': 12345}\" is not a valid value object",
        ],
    )


def test_not_valid_jsonld_format_missing_ids():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @id attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_id",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ["file descriptor does not contain the @id attribute"],
    )


def test_not_valid_jsonld_format_missing_types():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @type attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_type",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ["file descriptor does not contain the @type attribute"],
    )


def test_invalid_jsonld_context():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    The file descriptor contains an invalid context.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/invalid_context_uri",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ["Unable to retrieve the JSON-LD context 'https://w3id.org/ro/terms/invalid/context'"],
        profile_identifier="ro-crate-1.1",
        abort_on_first=True,
    )


def test_invalid_jsonld_not_compacted():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    The file descriptor is not compacted.
    """
    do_entity_test(
        paths.invalid_jsonld_not_compacted,
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ['The 1 occurrence of the "https://schema.org/name" URI cannot be used as a key'],
    )


def test_invalid_jsonld_unexpected_key():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    The file descriptor contains an unexpected key.
    """
    do_entity_test(
        paths.invalid_jsonld_unexpected_key,
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        [
            'The 1 occurrence of the JSON-LD key "hasPartx" is not allowed in the compacted format',
            'The 2 occurrences of the JSON-LD key "namex" are not allowed in the compacted format',
        ],
    )


def test_valid_jsonld_custom_term():
    """
    Test a RO-Crate with a valid JSON-LD file descriptor format
    which contains custom terms.
    """
    do_entity_test(ValidROC().rocrate_with_custom_terms, models.Severity.REQUIRED, True, [], [])


def test_singleton_entity_property_is_recommended_as_a_single_value():
    """
    Test the RO-Crate 1.1 recommendation that a singleton property array is
    represented as a single value in compacted JSON-LD.
    """
    do_entity_test(
        ValidROC().workflow_roc,
        models.Severity.RECOMMENDED,
        False,
        ["Entity properties compact representation"],
        ['property "name" SHOULD be represented as a single value'],
        profile_identifier="ro-crate-1.1",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
        rocrate_entity_patch={"sort-and-change-case.ga": {"name": ["sort-and-change-case"]}},
    )


def test_singleton_entity_property_remains_valid_at_required_severity():
    """A singleton property array is valid when only REQUIRED checks are run."""
    do_entity_test(
        ValidROC().workflow_roc,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.1",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
        rocrate_entity_patch={"sort-and-change-case.ga": {"name": ["sort-and-change-case"]}},
    )
