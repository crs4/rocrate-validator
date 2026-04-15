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
        skip_checks=["ro-crate-1.2_44.1"],
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
