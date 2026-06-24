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

import logging

from rocrate_validator import models, services
from tests.ro_crates import InvalidFileDescriptor, ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


# Global set up the paths
paths = InvalidFileDescriptor()


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
        profile_identifier="ro-crate",
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
