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
from tests.ro_crates_1_2 import ContextualEntities
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)

__contextual_entities_crates__ = ContextualEntities()

# Generic RECOMMENDED checks that fire on minimal test crates regardless of the
# contextual-entity-specific property being tested.
_GENERIC_RECOMMENDED_SKIP = [
    "ro-crate-1.2_47.1",   # Root Data Entity: RECOMMENDED funder
    "ro-crate-1.2_54.1",   # Root Data Entity: RECOMMENDED publisher
]

# Correct IDs for funder/publisher checks (used in person entity tests).
_PERSON_VALID_SKIP = [
    "ro-crate-1.2_47.1",   # Root Data Entity: RECOMMENDED funder
    "ro-crate-1.2_54.1",   # Root Data Entity: RECOMMENDED publisher
]


# ---------------------------------------------------------------------------
# License entity: SHOULD be typed as CreativeWork (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_license_entity():
    """
    A license entity with an absolute URL @id, CreativeWork type, name and
    description SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_license_entity,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_GENERIC_RECOMMENDED_SKIP,
    )


def test_invalid_license_entity_no_type():
    """
    A license entity missing `CreativeWork` in its @type SHOULD trigger a
    RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_license_entity_no_type,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["License entity: SHOULD be typed as CreativeWork"],
        expected_triggered_issues=[
            "A License entity SHOULD have `CreativeWork` in its `@type`"
        ],
    )


def test_invalid_license_entity_no_url():
    """
    A license entity whose @id is not an absolute HTTP(S) URL SHOULD trigger
    a RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_license_entity_no_url,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["License entity: SHOULD have absolute URL @id"],
        expected_triggered_issues=[
            "A License entity SHOULD have an absolute HTTP(S) URL as its @id"
        ],
    )


# ---------------------------------------------------------------------------
# License entity: name and description SHOULD be present (SHOULD)
# ---------------------------------------------------------------------------

def test_invalid_license_entity_no_name():
    """
    A license entity missing the `name` property SHOULD trigger a RECOMMENDED
    warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_license_entity_no_name,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["License entity: RECOMMENDED properties"],
        expected_triggered_issues=[
            "License entities SHOULD have a name"
        ],
    )


def test_invalid_license_entity_no_description():
    """
    A license entity missing the `description` property SHOULD trigger a
    RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_license_entity_no_description,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["License entity: RECOMMENDED properties"],
        expected_triggered_issues=[
            "License entities SHOULD have a description"
        ],
    )


# ---------------------------------------------------------------------------
# Organization entity: SHOULD have ROR identifier as @id (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_organization_entity():
    """
    An Organization entity with a ROR @id, contactPoint referencing ContactPoint,
    and author with contactPoint SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_organization_entity,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_GENERIC_RECOMMENDED_SKIP,
    )


def test_invalid_organization_no_ror_id():
    """
    An Organization entity whose @id is not a ROR identifier SHOULD trigger a
    RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_organization_no_ror_id,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Organization: SHOULD have ROR identifier"],
        expected_triggered_issues=[
            "An Organization entity SHOULD have a ROR identifier as its @id"
        ],
    )


# ---------------------------------------------------------------------------
# Organization/Person contactPoint: SHOULD reference ContactPoint entity (SHOULD)
# ---------------------------------------------------------------------------

def test_invalid_organization_contactpoint_no_entity():
    """
    An Organization whose contactPoint does not reference a ContactPoint entity
    SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_organization_contactpoint_no_entity,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Organization: SHOULD have contactPoint referencing ContactPoint"
        ],
        expected_triggered_issues=[
            "An Organization's contactPoint SHOULD reference a ContactPoint contextual entity"
        ],
    )


def test_invalid_organization_no_contactpoint():
    """
    An Organization without a contactPoint property (where the author still has
    contactPoint so only the Organization-specific check fires).
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_organization_no_contactpoint,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Organization: SHOULD have contactPoint referencing ContactPoint"
        ],
        expected_triggered_issues=[
            "An Organization's contactPoint SHOULD reference a ContactPoint contextual entity"
        ],
    )


# ---------------------------------------------------------------------------
# Author/Publisher: at least one SHOULD have contactPoint (SHOULD)
# ---------------------------------------------------------------------------

def test_invalid_no_author_publisher_contactpoint():
    """
    When neither the author nor the publisher Person/Organization has a
    contactPoint property, the Root Data Entity SHOULD trigger a
    RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_no_author_publisher_contactpoint,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Root Data Entity: at least one author/publisher SHOULD have contactPoint"
        ],
        expected_triggered_issues=[
            "At least one author or publisher Person/Organization SHOULD have a contactPoint property"
        ],
    )
