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
from tests.ro_crates_1_2 import AttachedROCrates, DetachedROCrates, MetadataDocument, MetadataDocumentFormat
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_document_crates__ = MetadataDocument()
__metadata_document_format_crates__ = MetadataDocumentFormat()

__attached_crates__ = AttachedROCrates()

__detached_crates__ = DetachedROCrates()


def test_valid_local_descriptor_filename():
    """
    Test that a local descriptor filename is valid in a detached RO-Crate.
    """
    do_entity_test(
        __detached_crates__.valid_local_descriptor_filename,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_local_descriptor_filename():
    """
    Test that a local descriptor filename is invalid in a detached RO-Crate.
    """
    do_entity_test(
        __detached_crates__.invalid_local_descriptor_filename,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Descriptor naming convention"],
        expected_triggered_issues=[
            "In a detached RO-Crate, "
            "the metadata descriptor filename SHOULD "
            "be named according to the convention "
            "`{prefix}-ro-crate-metadata.json`"]
    )
