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

from rocrate_validator import models
from tests.ro_crates_1_2 import MetadataDocument, MetadataDocumentFormat
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
        expected_triggered_issues=["RO-Crate file descriptor \"ro-crate-metadata.json\" is not UTF-8 encoded"]
    )


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
        expected_triggered_issues=[
            "RO-Crate file descriptor \"ro-crate-metadata.json\" "
            "is not in the correct format"
        ]
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
            "RO-Crate file descriptor \"ro-crate-metadata.json\" "
            "is not fully flattened at entity \"./\""
        ]
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
        expected_triggered_issues=[
            "The 1 occurrence of the \"https://schema.org/name\" URI "
            "cannot be used as a key"
        ]
    )


def test_invalid_context_reference():
    """
     Test that the metadata document is valid when it has an invalid context reference.
    """
    do_entity_test(
        __metadata_document_crates__.invalid_context_reference,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Descriptor JSON-LD format"],
        expected_triggered_issues=[
            "RO-Crate file descriptor \"ro-crate-metadata.json\" "
            "does not reference the required context \"https://w3id.org/ro/crate/1.2/context\""]
    )


def test_valid_context_reference():
    """
     Test that the metadata document is valid when it has a valid context reference.
    """
    do_entity_test(
        __metadata_document_crates__.valid_context_reference,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2"
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
        expected_triggered_issues=["Contextual entities SHOULD be referenced by other entities."]
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
        profile_identifier="ro-crate-1.2"
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
        profile_identifier="ro-crate-1.2"
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
            "Referenced contextual entities SHOULD be described in the same @graph"]
    )
