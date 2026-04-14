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
from tests.ro_crates_1_2 import AttachedROCrates, MetadataDocument, MetadataDocumentFormat, MetadataEntities
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_document_crates__ = MetadataDocument()
__metadata_document_format_crates__ = MetadataDocumentFormat()

__attached_crates__ = AttachedROCrates()

__metadata_entities__ = MetadataEntities()


def test_valid_recommended_schema_type():
    """
    Test that the metadata document includes at least one Schema.org type.
    """
    do_entity_test(
        __metadata_entities__.valid_recommended_schema_type,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2"

    )


def test_invalid_recommended_schema_type_warning():
    """
    Test that a warning is triggered when the metadata document
    does not include at least one Schema.org type.
    """
    do_entity_test(
        __metadata_entities__.invalid_recommended_schema_type,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["RO-Crate Metadata Entity RECOMMENDED type"],
        expected_triggered_issues=[
            "RO-Crate Metadata Entity SHOULD include at least one Schema.org type"]
    )
