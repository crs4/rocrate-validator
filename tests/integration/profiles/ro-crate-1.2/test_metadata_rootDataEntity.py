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
from tests.ro_crates_1_2 import RootDataEntity
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_root_data_entity_crates__ = RootDataEntity()


def test_valid_required_datePublished():
    """
    Test that the Root Data Entity is valid when it includes a `datePublished` property.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_required_datePublished,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2"

    )


def test_invalid_required_datePublished():
    """
    Test that the Root Data Entity is invalid when it does not include a `datePublished` property.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_required_datePublished,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["RO-Crate Root Data Entity REQUIRED properties"],
        expected_triggered_issues=[
            "The Root Data Entity MUST have a `datePublished` "
            "property (as specified by schema.org) with a valid ISO 8601 date"
        ]
    )
