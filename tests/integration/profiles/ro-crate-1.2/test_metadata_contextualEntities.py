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
from tests.ro_crates_v1_2 import ContextualEntities
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)

__contextual_entities_crates__ = ContextualEntities()

# Generic RECOMMENDED checks that fire on minimal test crates regardless of the
# contextual-entity-specific property being tested.
_GENERIC_RECOMMENDED_SKIP = [
    "ro-crate-1.2_48.1",   # Root Data Entity: RECOMMENDED funder
    "ro-crate-1.2_55.1",   # Root Data Entity: RECOMMENDED publisher
]

# Correct IDs for funder/publisher checks (used in person entity tests).
_PERSON_VALID_SKIP = [
    "ro-crate-1.2_48.1",   # Root Data Entity: RECOMMENDED funder
    "ro-crate-1.2_55.1",   # Root Data Entity: RECOMMENDED publisher
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


# ---------------------------------------------------------------------------
# Person entity: SHOULD have ORCID identifier as @id (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_person_entity():
    """
    A Person entity with an ORCID @id, contactPoint referencing ContactPoint,
    and affiliation referencing Organization SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_person_entity,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_PERSON_VALID_SKIP,
    )


def test_invalid_person_no_orcid():
    """
    A Person entity whose @id is not an ORCID identifier SHOULD trigger a
    RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_person_no_orcid,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Person: SHOULD have ORCID identifier"],
        expected_triggered_issues=[
            "A Person entity SHOULD have an ORCID identifier as its @id"
        ],
    )


def test_invalid_person_affiliation_not_org():
    """
    A Person entity whose affiliation does not reference an Organization
    SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_person_affiliation_not_org,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Person: RECOMMENDED affiliation"],
        expected_triggered_issues=[
            "Persons SHOULD reference an Organization for affiliation"
        ],
    )


# ---------------------------------------------------------------------------
# Any Contextual Entity: @id SHOULD be absolute URI or '#'-prefixed (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_contextual_entity_id_format():
    """
    A crate whose contextual entities all use absolute URI permalinks or
    '#'-prefixed local identifiers SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_contextual_entity_id_format,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_PERSON_VALID_SKIP,
    )


def test_invalid_bare_contactpoint_id():
    """
    A ContactPoint contextual entity with a bare relative @id (no '#', not an
    absolute URI) SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_contextual_entity_bare_contactpoint,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Entity identifier: format recommendations"],
        expected_triggered_issues=[
            "named local entities SHOULD use a '#'-prefixed @id"
        ],
    )


def test_invalid_bare_propertyvalue_id():
    """
    A PropertyValue contextual entity with a bare relative @id (no '#', not an
    absolute URI) SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_contextual_entity_bare_propertyvalue,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Entity identifier: format recommendations"],
        expected_triggered_issues=[
            "named local entities SHOULD use a '#'-prefixed @id"
        ],
    )


# ---------------------------------------------------------------------------
# SoftwareApplication / ComputerLanguage: MUST have name, url, version (REQUIRED)
# ---------------------------------------------------------------------------

def test_valid_software_application():
    """
    A SoftwareApplication contextual entity that declares `name`, `url`, and
    `version` MUST pass REQUIRED validation.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_software_application,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_software_application_no_version():
    """
    A SoftwareApplication contextual entity missing the `version` property
    MUST trigger a REQUIRED violation.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_software_application_no_version,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "SoftwareApplication or ComputerLanguage: REQUIRED `name`, `url`, `version`"
        ],
        expected_triggered_issues=[
            "A SoftwareApplication or ComputerLanguage MUST have a `version` property"
        ],
    )


def test_invalid_software_application_no_name():
    """
    A SoftwareApplication contextual entity missing the `name` property MUST
    trigger a REQUIRED violation.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_software_application_no_name,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "SoftwareApplication or ComputerLanguage: REQUIRED `name`, `url`, `version`"
        ],
        expected_triggered_issues=[
            "A SoftwareApplication or ComputerLanguage MUST have a `name` property"
        ],
    )


def test_invalid_software_application_no_url():
    """
    A SoftwareApplication contextual entity missing the `url` property MUST
    trigger a REQUIRED violation.
    """
    do_entity_test(
        __contextual_entities_crates__.invalid_software_application_no_url,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "SoftwareApplication or ComputerLanguage: REQUIRED `name`, `url`, `version`"
        ],
        expected_triggered_issues=[
            "A SoftwareApplication or ComputerLanguage MUST have a `url` property"
        ],
    )


def test_valid_computer_language():
    """
    A ComputerLanguage contextual entity (referenced as `programmingLanguage`
    of a Script) that declares `name`, `url`, `version`, and an optional
    `alternateName` MUST pass REQUIRED validation.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_computer_language,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


# ---------------------------------------------------------------------------
# Encoding format entity: MAY include `WebPageElement` when @id is a section
# of a webpage (sh:Info — optional suggestion) [5.8]
# ---------------------------------------------------------------------------

_ENCODING_FORMAT_MAY_REQUIREMENT = (
    "Encoding format: OPTIONAL `WebPageElement` type for section references"
)


def test_info_encoding_format_no_webpageelement():
    """
    An encoding format entity whose `@id` contains a fragment identifier
    (section of a webpage) but whose `@type` does NOT include `WebPageElement`
    triggers an `sh:Info` suggestion at OPTIONAL severity (RO-Crate 1.2, § 5.8).
    """
    do_entity_test(
        __contextual_entities_crates__.info_encoding_format_no_webpageelement,
        models.Severity.OPTIONAL,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[_ENCODING_FORMAT_MAY_REQUIREMENT],
        expected_triggered_issues=[
            "MAY include `WebPageElement` in its `@type`"
        ],
    )


def test_valid_encoding_format_with_webpageelement():
    """
    An encoding format entity whose `@id` contains a fragment identifier AND
    whose `@type` already includes `WebPageElement` does NOT trigger the MAY
    suggestion (the optional recommendation is satisfied).
    """
    from rocrate_validator import services
    result = services.validate({
        "rocrate_uri": str(
            __contextual_entities_crates__.valid_encoding_format_webpageelement
        ),
        "profile_identifier": "ro-crate-1.2",
        "requirement_severity": models.Severity.OPTIONAL,
    })
    failed_requirement_names = {
        issue.check.requirement.name for issue in result.get_issues()
    }
    assert _ENCODING_FORMAT_MAY_REQUIREMENT not in failed_requirement_names, (
        f"The MAY requirement {_ENCODING_FORMAT_MAY_REQUIREMENT!r} should NOT fire "
        f"when the encoding format entity already includes `WebPageElement` in its @type"
    )


def test_encoding_format_no_fragment_not_triggered():
    """
    An encoding format entity whose `@id` does NOT contain a fragment
    identifier is outside the target of the MAY shape; the suggestion must
    not fire.
    """
    from rocrate_validator import services
    result = services.validate({
        "rocrate_uri": str(__contextual_entities_crates__.encoding_format_no_fragment),
        "profile_identifier": "ro-crate-1.2",
        "requirement_severity": models.Severity.OPTIONAL,
    })
    failed_requirement_names = {
        issue.check.requirement.name for issue in result.get_issues()
    }
    assert _ENCODING_FORMAT_MAY_REQUIREMENT not in failed_requirement_names, (
        f"The MAY requirement {_ENCODING_FORMAT_MAY_REQUIREMENT!r} should NOT fire "
        f"when the encoding format entity @id does not contain a fragment identifier"
    )


# ---------------------------------------------------------------------------
# SoftwareApplication / ComputerLanguage: MAY have `alternateName` [5.7]
# ---------------------------------------------------------------------------

_SOFTWAREAPP_COMPUTERLANG_ALTERNATENAME_REQ = (
    "SoftwareApplication or ComputerLanguage: OPTIONAL `alternateName`"
)


def test_info_software_application_no_alternatename():
    """
    A SoftwareApplication contextual entity without an `alternateName`
    property triggers an `sh:Info` suggestion at OPTIONAL severity
    (RO-Crate 1.2, § 5.7).  The existing `valid` SoftwareApplication crate
    (used by `test_valid_software_application` at REQUIRED severity) is
    reused here: at REQUIRED it passes, at OPTIONAL the MAY suggestion fires.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_software_application,
        models.Severity.OPTIONAL,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[_SOFTWAREAPP_COMPUTERLANG_ALTERNATENAME_REQ],
        expected_triggered_issues=[
            "MAY declare an `alternateName` property"
        ],
    )


def test_valid_computer_language_with_alternatename_no_info():
    """
    A ComputerLanguage contextual entity that already declares an
    `alternateName` property does NOT trigger the MAY suggestion — the
    optional recommendation is satisfied.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_computer_language_with_alternatename,
        models.Severity.OPTIONAL,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_valid_computer_language_alternatename_passes_at_optional():
    """
    A minimal, fully-specified crate with a
    ComputerLanguage declaring `name`, `url`, `version`, and the MAY
    `alternateName` passes ALL validation checks including OPTIONAL-level
    INFO suggestions.
    """
    do_entity_test(
        __contextual_entities_crates__.valid_computer_language_with_alternatename,
        models.Severity.OPTIONAL,
        True,
        profile_identifier="ro-crate-1.2",
    )
