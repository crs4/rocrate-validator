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
from rocrate_validator.utils.http import HttpRequester
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


def test_valid_required_downloadable_citeAs(monkeypatch):
    """
    Test that the Root Data Entity is valid when it includes a `cite-as` property
    that references a downloadable item (mocked as application/zip via HEAD).
    """
    class _DownloadableResponse:
        status_code = 200
        headers = {"Content-Type": "application/zip"}
        links = {}

        def raise_for_status(self):
            pass

    def _fake_head(url, *args, **kwargs):
        logger.debug("Mock HEAD request to %s with args: %s, kwargs: %s", url, args, kwargs)
        return _DownloadableResponse()

    monkeypatch.setattr(HttpRequester(), "head", _fake_head)

    do_entity_test(
        __metadata_root_data_entity_crates__.valid_required_downloadable_citeAs,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
        enforce_availability=True,
    )


def test_invalid_required_downloadable_citeAs(monkeypatch):
    """
    Test that the Root Data Entity is invalid when it includes a `cite-as` property
    that does not reference a downloadable item (mocked as text/html via HEAD).
    """
    class _HtmlResponse:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        links = {}

        def raise_for_status(self):
            pass

    def _fake_head(url, *args, **kwargs):
        logger.debug("Mock HEAD request to %s with args: %s, kwargs: %s", url, args, kwargs)
        return _HtmlResponse()

    monkeypatch.setattr(HttpRequester(), "head", _fake_head)

    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_required_downloadable_citeAs,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        enforce_availability=True,
        expected_triggered_requirements=["Root Data Entity: `cite-as` downloadability"],
        expected_triggered_issues=[
            "MUST ultimately provide the RO-Crate as a downloadable item"
        ]
    )


def test_valid_recommended_citeAs_for_resolvable_id():
    """
    Test that the Root Data Entity is valid when it has a resolvable identifier
    and includes a `cite-as` property that references the Root Data Entity.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_citeAs_for_resolvable_id,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        # The test crate focuses on cite-as, not identifier format;
        # skip the identifier-presence and PropertyValue-approach checks.
        skip_checks=["ro-crate-1.2_51.1", "ro-crate-1.2_52.1"],
    )


def test_invalid_recommended_citeAs_for_resolvable_id():
    """
    Test that the Root Data Entity is invalid when it has a resolvable identifier
    and does not include a `cite-as` property that references the Root Data Entity.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_citeAs_for_resolvable_id,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Root Data Entity: use cite-as for resolvable identifiers"],
        expected_triggered_issues=[
            "If the Root Data Entity has a resolvable identifier, "
            "it SHOULD be included in the `cite-as` property of the RO-Crate Metadata Entity."
        ]
    )


def test_valid_additional_conformsTo_reference():
    """
    Test that the Root Data Entity is valid when it includes
    an additional `conformsTo` property that references a Profile entity.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_additional_conformsTo_reference,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_additional_conformsTo_reference():
    """
    Test that the Root Data Entity is invalid when it includes
    an additional `conformsTo` property that does not reference a Profile entity.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_additional_conformsTo_reference,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["RO-Crate Root Data Entity: optional `conformsTo` property value restriction"],
        expected_triggered_issues=[
            "If the Root Data Entity includes a `conformsTo` property, its values MUST reference Profile entities."
        ]
    )


# ---------------------------------------------------------------------------
# Root Data Entity identifier — persistent identifier resolution (RECOMMENDED)
# ---------------------------------------------------------------------------

class _ZipResponse:
    status_code = 200
    headers = {"Content-Type": "application/zip"}
    links = {}

    def raise_for_status(self):
        pass


class _HtmlResponse:
    status_code = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}
    links = {}

    def raise_for_status(self):
        pass


def test_valid_recommended_identifier_resolution(monkeypatch):
    """
    Root Data Entity whose identifier URL resolves to a downloadable resource
    (mocked as application/zip) passes the RECOMMENDED identifier resolution check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _ZipResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_identifier_resolution,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        # The identifier uses a plain URL string rather than a PropertyValue entity;
        # that format check is not the focus of this test (resolution is).
        skip_checks=["ro-crate-1.2_52.0"],
    )


def test_invalid_recommended_identifier_resolution(monkeypatch):
    """
    Root Data Entity whose identifier URL returns text/html (landing page) fails
    the RECOMMENDED identifier resolution check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _HtmlResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_identifier_resolution,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: persistent identifier resolution"],
        expected_triggered_issues=["SHOULD resolve to the RO-Crate Metadata Document or an archive"],
    )


# ---------------------------------------------------------------------------
# Root Data Entity: publisher SHOULD be present (RECOMMENDED)
# ---------------------------------------------------------------------------

def test_valid_recommended_publisher():
    """
    Root Data Entity with a publisher Organization passes the RECOMMENDED
    publisher check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_publisher,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_publisher():
    """
    Root Data Entity without a publisher fails the RECOMMENDED publisher check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_publisher,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: recommended publisher"],
        expected_triggered_issues=["SHOULD have a `publisher` property"],
    )


# ---------------------------------------------------------------------------
# Root Data Entity: funder SHOULD be present (RECOMMENDED — K1/K2/K3)
# ---------------------------------------------------------------------------

def test_valid_recommended_funding():
    """
    Root Data Entity with a funder Organization (which itself references an
    external funder) passes all RECOMMENDED funding checks.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_funding,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_funding_no_funder():
    """
    Root Data Entity with no `funder` property fails the RECOMMENDED
    direct-funder check (K3).
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_funding_no_funder,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: recommended funder"],
        expected_triggered_issues=["SHOULD reference funders directly via the `funder` property"],
    )


def test_invalid_recommended_funding_non_org_funder():
    """
    Root Data Entity whose `funder` references a Person (not an Organization)
    fails the RECOMMENDED funder-type check (K1).
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_funding_non_org_funder,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Funder entity: recommended Organization type"],
        expected_triggered_issues=["SHOULD be of type `Organization`"],
    )


def test_invalid_recommended_funding_no_project_funder():
    """
    Root Data Entity whose local project Organization (`funder`) does not itself
    reference an external funder fails the RECOMMENDED project-org funder check (K2).
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_funding_no_project_funder,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Project Organization: recommended funder reference"],
        expected_triggered_issues=["SHOULD itself reference an external `funder`"],
    )


# ---------------------------------------------------------------------------
# Root Data Entity: datePublished SHOULD specify at least day precision
# ---------------------------------------------------------------------------

def test_valid_recommended_datePublished_day_precision():
    """
    Root Data Entity with datePublished in YYYY-MM-DD format passes the
    RECOMMENDED day precision check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_datePublished_day_precision,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_35.1"],
    )


def test_invalid_recommended_datePublished_day_precision():
    """
    Root Data Entity with datePublished as just year (YYYY) fails the
    RECOMMENDED day precision check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_datePublished_day_precision,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: datePublished SHOULD specify at least day precision"],
        expected_triggered_issues=["SHOULD specify datePublished to at least the precision of a day"],
        skip_checks=["ro-crate-1.2_35.1"],
    )


# ---------------------------------------------------------------------------
# Root Data Entity: hasPart MUST reference all Data Entities
# ---------------------------------------------------------------------------

def test_valid_required_hasPart_all_data_entities():
    """
    Root Data Entity that references all Data Entities via hasPart (directly
    or indirectly) passes the REQUIRED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_required_hasPart_all_data_entities,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_46.1"],
    )


def test_invalid_required_hasPart_all_data_entities():
    """
    Root Data Entity that does NOT reference all Data Entities via hasPart
    fails the REQUIRED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_required_hasPart_all_data_entities,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: hasPart MUST reference all Data Entities"],
        expected_triggered_issues=["MUST reference all Data Entities via hasPart"],
        skip_checks=["ro-crate-1.2_46.1"],
    )


def test_invalid_hasPart_workflow_not_in_haspart():
    """
    A Workflow File entity (typed as File/SoftwareSourceCode/ComputationalWorkflow)
    that is not referenced via hasPart triggers the REQUIRED hasPart check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_hasPart_workflow_not_in_haspart,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: hasPart MUST reference all Data Entities"],
        expected_triggered_issues=["MUST reference all Data Entities via hasPart"],
    )


def test_invalid_hasPart_web_entity_not_in_haspart():
    """
    A Web Data Entity (absolute URL @id) that is not referenced via hasPart
    triggers the REQUIRED hasPart check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_hasPart_web_entity_not_in_haspart,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: hasPart MUST reference all Data Entities"],
        expected_triggered_issues=["MUST reference all Data Entities via hasPart"],
    )


def test_invalid_hasPart_dataset_not_in_haspart():
    """
    A sub-Dataset Directory Data Entity that is not referenced via hasPart
    triggers the REQUIRED hasPart check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_hasPart_dataset_not_in_haspart,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: hasPart MUST reference all Data Entities"],
        expected_triggered_issues=["MUST reference all Data Entities via hasPart"],
    )


# ---------------------------------------------------------------------------
# Root Data Entity: identifier SHOULD be present if PID exists (RECOMMENDED)
# ---------------------------------------------------------------------------

def test_valid_recommended_identifier_if_pid():
    """
    Root Data Entity with absolute URI @id and identifier property passes
    the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_identifier_if_pid,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_35.1", "ro-crate-1.2_38.1", "ro-crate-1.2_41.1",
                     "ro-crate-1.2_41.2", "ro-crate-1.2_41.3", "ro-crate-1.2_42.1",
                     "ro-crate-1.2_43.1", "ro-crate-1.2_43.2", "ro-crate-1.2_44.1",
                     "Root Data Entity: use cite-as for resolvable identifiers",
                     "Root Data Entity: persistent identifier resolution",
                     "Root Data Entity: identifier SHOULD be present if PID exists"],
        skip_availability_check=True,
    )


def test_invalid_recommended_identifier_if_pid():
    """
    Root Data Entity with absolute URI @id but no identifier property fails
    the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_identifier_if_pid,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: identifier SHOULD be present if PID exists"],
        expected_triggered_issues=["SHOULD have an `identifier` property if it has a persistent identifier"],
    )


# ---------------------------------------------------------------------------
# Root Data Entity: identifier SHOULD use PropertyValue approach (RECOMMENDED)
# ---------------------------------------------------------------------------

def test_valid_recommended_identifier_propertyvalue():
    """
    Root Data Entity that uses PropertyValue for identifier passes the
    RECOMMENDED check per Science On Schema.org.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_identifier_propertyvalue,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_35.1"],
    )


def test_invalid_recommended_identifier_propertyvalue():
    """
    Root Data Entity that uses plain string for identifier fails the
    RECOMMENDED PropertyValue approach check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_identifier_propertyvalue,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: identifier SHOULD use PropertyValue approach"],
        expected_triggered_issues=["SHOULD use PropertyValue entities for identifiers"],
    )


# ---------------------------------------------------------------------------
# Root Data Entity: conformsTo SHOULD be present if profiles exist (RECOMMENDED)
# ---------------------------------------------------------------------------

def test_valid_recommended_conformsto_if_profiles():
    """
    Root Data Entity that has a Profile entity in the graph and includes
    conformsTo on the Root passes the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_conformsto_if_profiles,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_35.1"],
    )


def test_invalid_recommended_conformsto_if_profiles():
    """
    Root Data Entity that has a Profile entity in the graph but does NOT
    include conformsTo on the Root fails the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_conformsto_if_profiles,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Root Data Entity: conformsTo SHOULD be present if profiles exist"],
        expected_triggered_issues=["SHOULD have a `conformsTo` property if the RO-Crate conforms to profiles"],
    )
