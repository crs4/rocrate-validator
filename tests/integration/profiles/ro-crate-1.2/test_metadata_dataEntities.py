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
from tests.ro_crates_1_2 import DataEntities
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_root_data_entity_crates__ = DataEntities()


def test_valid_local_entity_reference():
    """
    Test that a Data Entity is valid when it references a local file using a relative path in its `@id`.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_local_entity_reference,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_local_entity_reference():
    """
    Test that a Data Entity is invalid when it references a local file using an absolute path in its `@id`.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_local_entity_reference,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Data Entity: identifier requirements"],
        expected_triggered_issues=[
            "MUST use a relative @id within the RO-Crate root"
        ]
    )


def test_valid_detached_rocrate_dataEntities():
    """
    Test that a Data Entity is valid when it references a remote file using an absolute URI in its `@id`.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_detached_rocrate_dataEntities,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_detached_rocrate_dataEntities():
    """
    Test that a Data Entity is invalid when it references a remote file using a relative path in its `@id`.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_detached_rocrate_dataEntities,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Data Entity: identifier requirements"],
        expected_triggered_issues=[
            "has a local identifier but the Root Data Entity does not have a local identifier"
        ]
    )


def test_valid_recommended_properties():
    """
    Test that a Data Entity is valid when it includes recommended properties.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_properties,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_recommended_properties():
    """
    Test that a Data Entity is invalid when it includes recommended properties.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_properties,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Data Entity: RECOMMENDED properties"],
        expected_triggered_issues=[
            "Data Entities SHOULD have a `name` property",
            "Data Entities SHOULD have a `description` property"
        ]
    )
