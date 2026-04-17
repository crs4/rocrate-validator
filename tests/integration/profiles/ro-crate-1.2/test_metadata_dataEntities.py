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
from tests.ro_crates_v1_2 import DataEntities
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
    Test that a Data Entity is invalid when it lacks recommended properties.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_properties,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Data Entity: RECOMMENDED properties"],
        expected_triggered_issues=[
            "Data Entities SHOULD have a `name` property",
            "Data Entities SHOULD have a `description` property",
        ]
    )


def test_valid_recommended_encoding_format():
    """
    Test that a Data Entity is valid when it includes the recommended `encodingFormat` property.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_encoding_format,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_recommended_encoding_format():
    """
    Test that a Data Entity is invalid when it includes an invalid value for the recommended `encodingFormat` property.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_encoding_format,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Data Entity: RECOMMENDED `encodingFormat` property"],
        expected_triggered_issues=[
            "Missing or invalid `encodingFormat` linked to the `File Data Entity`"
        ]
    )


# ---------------------------------------------------------------------------
# Web entity @id — downloadability (MUST at creation_time / enforce_availability)
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


def test_valid_required_web_entity_downloadable(monkeypatch):
    """
    Web-based Data Entity whose @id returns a non-HTML Content-Type MUST pass
    the availability check when enforce_availability=True.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _ZipResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.valid_web_entity_downloadable,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
        enforce_availability=True,
    )


def test_invalid_required_web_entity_not_downloadable(monkeypatch):
    """
    Web-based Data Entity whose @id returns text/html (splash page) MUST fail
    the availability check when enforce_availability=True.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _HtmlResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_web_entity_splash_page,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        enforce_availability=True,
        expected_triggered_requirements=["Web-based Data Entity: REQUIRED availability"],
        expected_triggered_issues=["HTML page"],
    )


# ---------------------------------------------------------------------------
# Web entity @id — availability warning (RECOMMENDED, default mode)
# ---------------------------------------------------------------------------

def test_valid_recommended_web_entity_downloadable_warning(monkeypatch):
    """
    Web-based Data Entity whose @id returns application/zip passes the
    RECOMMENDED availability check in default mode.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _ZipResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.valid_web_entity_downloadable,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_web_entity_splash_page_warning(monkeypatch):
    """
    Web-based Data Entity whose @id returns text/html triggers a RECOMMENDED
    warning about a possible splash page in default mode.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _HtmlResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_web_entity_splash_page,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Web-based Data Entity: REQUIRED availability"],
        expected_triggered_issues=["HTML page"],
    )


# ---------------------------------------------------------------------------
# Web entity contentUrl — downloadability (RECOMMENDED)
# ---------------------------------------------------------------------------

def test_valid_recommended_content_url_downloadable(monkeypatch):
    """
    Web-based Data Entity whose contentUrl returns application/zip passes the
    RECOMMENDED contentUrl availability check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _ZipResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_content_url,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_content_url_not_downloadable(monkeypatch):
    """
    Web-based Data Entity whose contentUrl returns text/html fails the
    RECOMMENDED contentUrl availability check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _HtmlResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_content_url,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Web-based Data Entity: REQUIRED availability"],
        expected_triggered_issues=["contentUrl", "not directly downloadable"],
    )


def test_valid_missing_file_local_path():
    """
    A missing local file that declares localPath, and a deliberately absent
    file (#id) that declares localPath, SHOULD both pass the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_missing_file_local_path,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_16.1", "ro-crate-1.2_38.1",
                     "ro-crate-1.2_17.1", "ro-crate-1.2_39.0", "ro-crate-1.2_39.1",
                     "ro-crate-1.2_18.1"],
    )


def test_invalid_missing_file_no_local_path():
    """
    A missing local file without localPath and a deliberately absent file (#id)
    without localPath SHOULD each trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_missing_file_local_path,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_16.1"],
        expected_triggered_requirements=[
            "Data Entity: missing file SHOULD use localPath"
        ],
        expected_triggered_issues=[
            "localPath"
        ],
    )


def test_valid_data_entity_license_divergence():
    """
    A Data Entity with a different license from the Root SHOULD pass
    the RECOMMENDED check (the entity is correctly overriding the
    default license).
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_data_entity_license_divergence,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_16.1", "ro-crate-1.2_38.1"],
    )


def test_invalid_data_entity_redundant_license():
    """
    A Data Entity that declares the same license as the Root SHOULD
    still pass validation, but a warning SHOULD be logged about the
    redundant license declaration.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_data_entity_license_divergence,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_16.1", "ro-crate-1.2_38.1"],
    )


def test_redundant_license_logs_warning():
    """
    When a Data Entity declares the same license as the Root, a warning
    message SHOULD be logged (not a validation issue).  The validation
    result MUST pass, and the warning MUST appear in the log stream.
    """
    from rocrate_validator.utils.log import __log_stream__

    # Clear any previous log output
    __log_stream__.truncate(0)
    __log_stream__.seek(0)

    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_data_entity_license_divergence,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_16.1", "ro-crate-1.2_38.1"],
    )

    log_contents = __log_stream__.getvalue()
    assert "redundant" in log_contents.lower(), \
        f"Expected a warning log about redundant license, got:\n{log_contents}"


# ---------------------------------------------------------------------------
# File Data Entity — contentSize (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_recommended_contentSize():
    """
    A File Data Entity with the recommended `contentSize` property SHOULD pass
    the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_contentSize,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_recommended_contentSize():
    """
    A File Data Entity without the recommended `contentSize` property SHOULD
    fail the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_contentSize,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File Data Entity: RECOMMENDED contentSize"],
        expected_triggered_issues=["contentSize"]
    )


# ---------------------------------------------------------------------------
# File Data Entity — conformsTo profile (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_recommended_conformsto():
    """
    A File Data Entity whose `conformsTo` references a CreativeWork or Profile
    SHOULD pass the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_conformsto,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2"
    )


def test_invalid_recommended_conformsto():
    """
    A File Data Entity whose `conformsTo` references a non-Profile/non-CreativeWork
    entity SHOULD fail the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_conformsto,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["File: RECOMMENDED `conformsTo` profile"],
        expected_triggered_issues=["conformsTo"]
    )


# ---------------------------------------------------------------------------
# Web-based File Data Entity — sdDatePublished (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_recommended_sdDatePublished(monkeypatch):
    """
    A web-based File Data Entity with the recommended `sdDatePublished` property
    SHOULD pass the RECOMMENDED check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _ZipResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_sdDatePublished,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_sdDatePublished(monkeypatch):
    """
    A web-based File Data Entity without the recommended `sdDatePublished` property
    SHOULD fail the RECOMMENDED check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _ZipResponse())

    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_sdDatePublished,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Web-based Data Entity: RECOMMENDED properties"],
        expected_triggered_issues=["sdDatePublished"]
    )


# ---------------------------------------------------------------------------
# 4.3 Dataset (Directory) Data Entity — trailing slash (RECOMMENDED)
# ---------------------------------------------------------------------------

def test_valid_recommended_dataset_trailing_slash():
    """
    A local Dataset Data Entity whose @id ends with '/' passes the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_dataset_trailing_slash,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        metadata_only=True,
    )


def test_invalid_recommended_dataset_trailing_slash():
    """
    A local Dataset Data Entity whose @id does NOT end with '/' fails the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_dataset_trailing_slash,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        metadata_only=True,
        expected_triggered_requirements=["Dataset Data Entity: SHOULD end with trailing slash"],
        expected_triggered_issues=["The @id of a local Dataset Data Entity SHOULD end with '/'"],
    )


# ---------------------------------------------------------------------------
# 4.3 Dataset (Directory) Data Entity — hasPart (RECOMMENDED)
# ---------------------------------------------------------------------------

def test_valid_recommended_dataset_has_part():
    """
    A local Dataset Data Entity that lists its contents via hasPart passes
    the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.valid_recommended_dataset_has_part,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        metadata_only=True,
    )


def test_invalid_recommended_dataset_has_part():
    """
    A local Dataset Data Entity without a hasPart property fails the RECOMMENDED check.
    """
    do_entity_test(
        __metadata_root_data_entity_crates__.invalid_recommended_dataset_has_part,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        metadata_only=True,
        expected_triggered_requirements=["Dataset Data Entity: SHOULD have hasPart"],
        expected_triggered_issues=["Local Dataset Data Entities SHOULD list their contents via `hasPart`"],
    )
