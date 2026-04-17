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
        profile_identifier="ro-crate-1.2"
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
        expected_triggered_issues=[
            "The RO-Crate metadata file descriptor SHOULD have a single `conformsTo` value"
        ]
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
        profile_identifier="ro-crate-1.2"
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
        ]
    )
