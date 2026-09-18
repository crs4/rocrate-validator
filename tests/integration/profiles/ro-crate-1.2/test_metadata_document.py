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
from unittest.mock import MagicMock

import pytest

from rocrate_validator import models, services
from rocrate_validator.errors import ROCrateMetadataNotFoundError
from rocrate_validator.models import requirement as requirement_module
from rocrate_validator.requirements.shacl import requirements as shacl_requirements_module
from rocrate_validator.rocrate.plain import ROCrateLocalFolder
from rocrate_validator.utils.uri import URI
from tests.ro_crates_v1_2 import MetadataDocument, MetadataDocumentFormat
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_document_crates__ = MetadataDocument()
__metadata_document_format_crates__ = MetadataDocumentFormat()


def test_not_utf8():
    """
    Test that the metadata document is valid when it is not UTF-8 encoded.
    """
    do_entity_test(
        __metadata_document_format_crates__.not_utf8,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Descriptor UTF-8 encoding"],
        expected_triggered_issues=['RO-Crate file descriptor "ro-crate-metadata.json" is not UTF-8 encoded'],
    )


def test_utf8_check_is_skipped_for_metadata_dict(monkeypatch, tmp_path):
    """Metadata-only validation must not read a file descriptor from the CWD."""
    crate_path = __metadata_document_crates__.valid_context_reference
    with (crate_path / "ro-crate-metadata.json").open(encoding="utf-8") as stream:
        metadata_dict = json.load(stream)

    descriptor_reads = []
    original_get_file_content = ROCrateLocalFolder.get_file_content

    def track_descriptor_reads(crate, path, binary_mode=True):
        if path.name == "ro-crate-metadata.json":
            descriptor_reads.append((path, binary_mode))
        return original_get_file_content(crate, path, binary_mode)

    monkeypatch.setattr(ROCrateLocalFolder, "get_file_content", track_descriptor_reads)
    monkeypatch.chdir(tmp_path)
    do_entity_test(
        crate_path,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
        metadata_dict=metadata_dict,
        metadata_only=True,
    )
    assert descriptor_reads == []


def test_missing_descriptor_does_not_emit_unexpected_warnings(monkeypatch, tmp_path):
    """Checks depending on metadata should defer to the descriptor checks."""
    requirement_logger = MagicMock()
    shacl_logger = MagicMock()
    monkeypatch.setattr(requirement_module, "logger", requirement_logger)
    monkeypatch.setattr(shacl_requirements_module, "logger", shacl_logger)

    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=URI(tmp_path),
            profile_identifier="ro-crate-1.2",
            requirement_severity=models.Severity.OPTIONAL,
        )
    )

    issues = [issue.message for issue in result.get_issues()]
    assert result.passed() is False
    assert any(
        issue is not None and 'file descriptor "ro-crate-metadata.json" is not present' in issue for issue in issues
    )
    assert not any(
        issue is not None
        and any(message in issue for message in ("Unexpected error", "Error checking", "not in the correct format"))
        for issue in issues
    )
    assert requirement_logger.warning.call_count == 0
    assert shacl_logger.warning.call_count == 0


def test_missing_descriptor_raises_specific_metadata_error(tmp_path):
    """Reading a missing descriptor must preserve its metadata-specific cause."""
    crate = ROCrateLocalFolder(tmp_path)

    with pytest.raises(ROCrateMetadataNotFoundError) as error:
        crate.metadata.as_dict()

    assert error.value.path == "ro-crate-metadata.json"
    assert isinstance(error.value.__cause__, FileNotFoundError)


def test_not_json():
    """
    Test that the metadata document is valid when it is not JSON-LD.
    """
    do_entity_test(
        __metadata_document_format_crates__.not_jsonld,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Descriptor JSON format"],
        expected_triggered_issues=['RO-Crate file descriptor "ro-crate-metadata.json" is not valid JSON'],
    )


def test_not_flattened():
    """
    Test that the metadata document is valid when it is not flattened.
    """
    do_entity_test(
        __metadata_document_format_crates__.not_flattened,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Descriptor JSON-LD format"],
        expected_triggered_issues=[
            'RO-Crate file descriptor "ro-crate-metadata.json" is not fully flattened at entity "./"'
        ],
    )


def test_not_compacted():
    """
    Test that the metadata document is valid when it is not compacted.
    """
    do_entity_test(
        __metadata_document_format_crates__.not_compacted,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Descriptor JSON-LD format"],
        expected_triggered_issues=['The 1 occurrence of the "https://schema.org/name" URI cannot be used as a key'],
    )


def test_invalid_context_reference():
    """
    Test that the metadata document is invalid when it has an invalid context reference.
    """
    do_entity_test(
        __metadata_document_crates__.invalid_context_reference,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Descriptor JSON-LD format"],
        expected_triggered_issues=[
            (
                'RO-Crate file descriptor "ro-crate-metadata.json" '
                'does not reference the required context "https://w3id.org/ro/crate/1.2/context"'
            )
        ],
    )


def test_valid_context_reference():
    """
    Test that the metadata document is valid when it has a valid context reference.
    """
    do_entity_test(
        __metadata_document_crates__.valid_context_reference,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_singleton_entity_property_is_recommended_as_a_single_value():
    """
    Test the RO-Crate 1.2 recommendation that a singleton property array is
    represented as a single value in compacted JSON-LD.
    """
    do_entity_test(
        __metadata_document_crates__.valid_context_reference,
        models.Severity.RECOMMENDED,
        False,
        ["Entity properties compact representation"],
        ['property "hasPart" SHOULD be represented as a single value'],
        profile_identifier="ro-crate-1.2",
    )


def test_not_referenced_contextual_entity():
    """
    Test that the metadata document is not valid
    when it has a contextual entity that is not referenced by any other entity in the graph.
    """
    do_entity_test(
        __metadata_document_crates__.not_referenced_contextual_entity,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Contextual Entity RECOMMENDED references"],
        expected_triggered_issues=["Contextual entities SHOULD be referenced by other entities."],
    )


def test_referenced_contextual_entity():
    """
    Test that the metadata document is valid
    when it has a contextual entity that is referenced by other entities in the graph.
    """
    do_entity_test(
        __metadata_document_crates__.valid_referenced_contextual_entity,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_described_contextual_entity():
    """
    Test that the metadata document is valid
    when it has a contextual entity that is described in the same graph.
    """
    do_entity_test(
        __metadata_document_crates__.described_contextual_entity,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_not_described_contextual_entity():
    """
    Test that the metadata document is not valid
    when it has a contextual entity that is not described in the same graph.
    """
    do_entity_test(
        __metadata_document_crates__.not_described_contextual_entity,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Contextual Entity RECOMMENDED description"],
        expected_triggered_issues=[
            (
                "Contextual entities that are referenced by other entities SHOULD be "
                "described in the same @graph, with at least an RDF type specified."
            )
        ],
    )


# ---------------------------------------------------------------------------
# @id format: no ../ parent traversal (RECOMMENDED)
# ---------------------------------------------------------------------------


def test_valid_no_parent_traversal():
    """
    Crate with clean relative @id paths passes the no-../  check.
    """
    do_entity_test(
        __metadata_document_crates__.valid_no_parent_traversal,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_no_parent_traversal():
    """
    Crate with an entity @id containing ../ fails the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_document_crates__.invalid_no_parent_traversal,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Entity identifier: format recommendations"],
        expected_triggered_issues=["SHOULD NOT contain '../'"],
    )


# ---------------------------------------------------------------------------
# @id format: native UTF-8, not percent-encoded (RECOMMENDED)
# ---------------------------------------------------------------------------


def test_valid_utf8_identifiers():
    """
    Crate with native UTF-8 characters in @id passes the encoding check.
    """
    do_entity_test(
        __metadata_document_crates__.valid_utf8_identifiers,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_utf8_identifiers():
    """
    Crate with percent-encoded non-ASCII bytes in @id fails the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_document_crates__.invalid_utf8_identifiers,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Entity identifier: format recommendations"],
        expected_triggered_issues=["percent-encoded non-ASCII characters"],
    )


# ---------------------------------------------------------------------------
# @id format: named contextual entity SHOULD use # prefix (RECOMMENDED)
# ---------------------------------------------------------------------------


def test_valid_named_entity_id_format():
    """
    Crate where local Person/Organization entities use '#'-prefixed @id passes.
    """
    do_entity_test(
        __metadata_document_crates__.valid_named_entity_id_format,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_named_entity_id_format():
    """
    Crate where a local Person entity uses a bare relative @id (no '#') fails.
    """
    do_entity_test(
        __metadata_document_crates__.invalid_named_entity_id_format,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Entity identifier: format recommendations"],
        expected_triggered_issues=["named local entities SHOULD use a '#'-prefixed @id"],
    )


# ---------------------------------------------------------------------------
# Schema.org IRIs: http namespace, not https (MUST) — see #188
# ---------------------------------------------------------------------------


def test_valid_schema_org_iri_protocol():
    """
    Crate whose Schema.org IRIs all use the http namespace passes.
    """
    do_entity_test(
        __metadata_document_crates__.valid_schema_org_iri_protocol,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_schema_org_type_protocol():
    """
    An entity typed with an https Schema.org IRI is reported, naming the http term.
    """
    do_entity_test(
        __metadata_document_crates__.invalid_schema_org_iri_protocol,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Schema.org @type protocol"],
        expected_triggered_issues=[
            "declares the @type 'https://schema.org/Organization'",
            "MUST be typed 'Organization' (i.e. 'http://schema.org/Organization')",
        ],
    )


def test_schema_org_type_presence_check_accepts_https_namespace():
    """
    The existing Schema.org type recommendation remains a presence check and
    must not duplicate the dedicated protocol check.
    """
    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=models.URI(__metadata_document_crates__.invalid_schema_org_iri_protocol),
            requirement_severity=models.Severity.RECOMMENDED,
            profile_identifier="ro-crate-1.2",
        )
    )
    assert any(detail.check.requirement.name == "Schema.org @type protocol" for detail in result.get_issues())
    assert not any(
        issue.message == "RO-Crate Metadata Entity SHOULD include at least one Schema.org type"
        for issue in result.get_issues()
    )


def test_https_schema_org_id_is_allowed():
    """
    An https Schema.org IRI used as an @id remains a valid resource identifier.
    """
    do_entity_test(
        __metadata_document_crates__.valid_schema_org_iri_protocol,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
        rocrate_entity_patch={"#uuid": {"propertyID": {"@id": "https://schema.org/identifier"}}},
    )


def test_https_entity_id_is_not_recommended():
    """
    An entity's own HTTPS Schema.org @id is not a compatibility issue.
    """
    with (__metadata_document_crates__.valid_schema_org_iri_protocol / "ro-crate-metadata.json").open(
        encoding="utf-8"
    ) as stream:
        metadata_dict = json.load(stream)
    metadata_dict["@graph"].append(
        {
            "@id": "https://schema.org/StandaloneResource",
            "@type": "Thing",
            "name": "Standalone Schema.org resource",
        }
    )
    do_entity_test(
        __metadata_document_crates__.valid_schema_org_iri_protocol,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        metadata_dict=metadata_dict,
        metadata_only=True,
    )


def test_https_nested_schema_org_id_is_recommended_for_compatibility():
    """
    A nested HTTPS Schema.org @id remains valid but emits a compatibility recommendation.
    """
    do_entity_test(
        __metadata_document_crates__.valid_schema_org_iri_protocol,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        rocrate_entity_patch={"#uuid": {"propertyID": {"@id": "https://schema.org/identifier"}}},
        expected_triggered_requirements=["Schema.org @id compatibility"],
        expected_triggered_issues=[
            "references the Schema.org IRI 'https://schema.org/identifier' through a nested @id",
            "SHOULD use 'identifier' (i.e. 'http://schema.org/identifier')",
        ],
    )


def test_schema_org_protocol_shapes_run_after_context_check():
    """
    The context check runs before the SHACL protocol shapes. A context failure
    is reported, while the protocol shapes do not emit unrelated violations.
    """
    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=models.URI(__metadata_document_crates__.invalid_context_reference),
            requirement_severity=models.Severity.RECOMMENDED,
            profile_identifier="ro-crate-1.2",
        )
    )

    protocol_issues = {
        issue.check.requirement.name
        for issue in result.get_issues()
        if issue.check.requirement.name in {"Schema.org @type protocol", "Schema.org @id compatibility"}
    }
    assert protocol_issues == set()
    assert any(
        issue.message
        and 'does not reference the required context "https://w3id.org/ro/crate/1.2/context"' in issue.message
        for issue in result.get_issues()
    )
    assert not any(
        detail.check.requirement.name in {"Schema.org @type protocol", "Schema.org @id compatibility"}
        for detail in result.skipped_check_details
    )
