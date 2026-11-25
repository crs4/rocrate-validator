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

from rocrate_validator import models, services
from rocrate_validator.models.profile_detection import detect_rocrate_profiles
from tests.ro_crates_v1_2 import MetadataDescriptor, MetadataDocument, MetadataDocumentFormat
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_document_crates__ = MetadataDocument()
__metadata_document_format_crates__ = MetadataDocumentFormat()

__metadata_descriptor_crates__ = MetadataDescriptor()


def test_valid_single_value_conformsTo():
    """
    Test that the metadata descriptor is valid when the `conformsTo` property
    includes a single value.
    """
    do_entity_test(
        __metadata_descriptor_crates__.valid_single_value_conformsTo,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_single_value_conformsTo():
    """
    Test that the metadata descriptor is invalid when the `conformsTo` property
    includes multiple values.
    """
    do_entity_test(
        __metadata_descriptor_crates__.invalid_single_value_conformsTo,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["RO-Crate Metadata File Descriptor RECOMMENDED conformsTo"],
        expected_triggered_issues=["The RO-Crate metadata file descriptor SHOULD have a single `conformsTo` value"],
    )


def test_valid_recommended_prefix_conformsTo():
    """
    Test that the metadata descriptor is valid when the `conformsTo` property
    includes a value with the recommended prefix.
    """
    do_entity_test(
        __metadata_descriptor_crates__.valid_recommended_prefix_conformsTo,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_prefix_conformsTo():
    """
    Test that the metadata descriptor is invalid when the `conformsTo` property
    includes a value with an incorrect prefix.
    """
    do_entity_test(
        __metadata_descriptor_crates__.invalid_recommended_prefix_conformsTo,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["RO-Crate Metadata File Descriptor RECOMMENDED conformsTo"],
        expected_triggered_issues=[
            "The RO-Crate metadata file descriptor `conformsTo` URI SHOULD start with https://w3id.org/ro/crate/"
        ],
    )


def test_invalid_string_conformsTo_is_reported_at_required_severity():
    """A literal conformsTo value must be reported even with explicit profile selection."""
    do_entity_test(
        __metadata_descriptor_crates__.valid_single_value_conformsTo,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        rocrate_entity_patch={
            "ro-crate-metadata.json": {"conformsTo": "https://w3id.org/ro/crate/1.2"},
        },
        expected_triggered_issues=[
            "Each RO-Crate Metadata Descriptor `conformsTo` value MUST be a reference object containing `@id`",
        ],
    )


def test_referenced_external_metadata_descriptor_does_not_shadow_primary(tmp_path):
    """
    A referenced `.../ro-crate-metadata.json` from another crate must not be
    classified as `ROCrateMetadataFileDescriptor` or shadow `ro-crate-metadata.json`
    during profile auto-detection (issue #258).
    """
    metadata_dict = {
        "@context": "https://w3id.org/ro/crate/1.2/context",
        "@graph": [
            {
                "@id": "https://example.org/other/ro-crate-metadata.json",
                "@type": "File",
                "name": "Referenced RO-Crate metadata",
                "about": {"@id": "./"},
            },
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
                "about": {"@id": "./"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": "Example crate",
                "description": "Crate referencing another crate's metadata descriptor",
                "datePublished": "2026-11-17",
                "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
                "hasPart": [{"@id": "https://example.org/other/ro-crate-metadata.json"}],
            },
        ],
    }
    (tmp_path / "ro-crate-metadata.json").write_text(json.dumps(metadata_dict), encoding="utf-8")

    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=models.URI(str(tmp_path)),
            profile_identifier="ro-crate-1.2",
            requirement_severity=models.Severity.REQUIRED,
            metadata_only=True,
        )
    )
    assert result.passed(), [issue.message for issue in result.get_issues()]

    # Also verify profile auto-detection when the file is a detached prefixed descriptor
    # and the referenced descriptor is typed as CreativeWork.
    metadata_dict["@graph"][0]["@type"] = ["File", "CreativeWork"]
    detached_file = tmp_path / "custom-ro-crate-metadata.json"
    detached_file.write_text(json.dumps(metadata_dict), encoding="utf-8")
    detached_settings = models.ValidationSettings(rocrate_uri=models.URI(str(detached_file)), metadata_only=True)
    context = models.ValidationContext(models.Validator(detached_settings), detached_settings)
    detection = detect_rocrate_profiles(context)
    assert [p.identifier for p in detection.profiles] == ["ro-crate-1.2"]
