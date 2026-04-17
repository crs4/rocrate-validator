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
from tests.ro_crates_v1_2 import AttachedROCrates, MetadataDocument, MetadataDocumentFormat
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_document_crates__ = MetadataDocument()
__metadata_document_format_crates__ = MetadataDocumentFormat()

__attached_crates__ = AttachedROCrates()


def test_preview_not_in_hasPart():
    """
    Test that the metadata document is valid when the preview file
    is not included in the `hasPart` property of the Root Data Entity.
    """
    do_entity_test(
        __attached_crates__.valid_preview_not_in_hasPart,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2"

    )


def test_preview_not_in_hasPart_warning():
    """
    Test that a warning is triggered when the preview file
    is not included in the `hasPart` property of the Root Data Entity.
    """
    do_entity_test(
        __attached_crates__.invalid_preview_not_in_hasPart,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Preview file descriptor should not be included in `hasPart`"],
        expected_triggered_issues=[
            "RO-Crate Website files SHOULD NOT be included in `hasPart`"]
    )


def test_root_with_IRI_identifier():
    do_entity_test(
        __attached_crates__.valid_relative_root_entity_id,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_root_with_relative_identifier():
    do_entity_test(
        __attached_crates__.valid_relative_root_entity_id,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_root_with_invalid_relative_identifier():
    do_entity_test(
        __attached_crates__.invalid_relative_root_entity_id,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity identifier restriction"],
        expected_triggered_issues=[
            "The Root Data Entity MUST be a `Dataset` (as per `schema.org`) and use an IRI or `./` as identifier"]
    )


def test_root_with_invalid_non_relative_identifier():
    do_entity_test(
        __attached_crates__.invalid_non_relative_root_entity_id,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity identifier restriction"],
        expected_triggered_issues=[
            "The Root Data Entity MUST be a `Dataset` (as per `schema.org`) and use an IRI or `./` as identifier"]
    )
