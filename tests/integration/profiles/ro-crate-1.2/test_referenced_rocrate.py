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
from tests.ro_crates_v1_2 import ReferencedROCrates
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)

__referenced_rocrate_crates__ = ReferencedROCrates()


def test_valid_referenced_rocrate():
    """
    A crate referencing another RO-Crate with all recommended properties
    SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __referenced_rocrate_crates__.valid,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_40.0", "ro-crate-1.2_45.1", "ro-crate-1.2_70.1", "ro-crate-1.2_73.1"],
    )


def test_invalid_referenced_rocrate_no_versionless_conformsto():
    """
    A referenced RO-Crate data entity missing the version-less conformsTo
    SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __referenced_rocrate_crates__.invalid_no_versionless_conformsto,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Referenced RO-Crate: SHOULD include version-less profile in conformsTo"
        ],
        expected_triggered_issues=[
            "version-less"
        ],
    )


def test_invalid_root_conformsto_versionless():
    """
    The Root Data Entity MUST NOT declare the version-less conformsTo profile URI.
    """
    do_entity_test(
        __referenced_rocrate_crates__.invalid_root_conformsto_versionless,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "RO-Crate Root Data Entity: MUST NOT declare version-less conformsTo profile"
        ],
        expected_triggered_issues=[
            "version-less"
        ],
    )


def test_invalid_referenced_rocrate_no_subjectof():
    """
    A referenced RO-Crate data entity missing subjectOf SHOULD trigger
    a RECOMMENDED warning.
    """
    do_entity_test(
        __referenced_rocrate_crates__.invalid_no_subjectof,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Referenced RO-Crate: SHOULD have subjectOf"
        ],
        expected_triggered_issues=[
            "subjectOf"
        ],
    )


def test_invalid_referenced_rocrate_md_encoding_format():
    """
    A referenced RO-Crate metadata descriptor with wrong encodingFormat
    SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __referenced_rocrate_crates__.invalid_md_encoding_format,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Referenced RO-Crate metadata descriptor: recommended properties"
        ],
        expected_triggered_issues=[
            "encodingFormat"
        ],
    )


def test_invalid_referenced_rocrate_md_conformsto():
    """
    A referenced RO-Crate metadata descriptor with conformsTo SHOULD trigger
    a RECOMMENDED warning (conformsTo belongs on the data entity).
    """
    do_entity_test(
        __referenced_rocrate_crates__.invalid_md_conformsto,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Referenced RO-Crate metadata descriptor: recommended properties"
        ],
        expected_triggered_issues=[
            "conformsTo"
        ],
    )


def test_invalid_referenced_rocrate_md_about():
    """
    A referenced RO-Crate metadata descriptor with about SHOULD trigger
    a RECOMMENDED warning (about belongs on the crate's own metadata descriptor).
    """
    do_entity_test(
        __referenced_rocrate_crates__.invalid_md_about,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Referenced RO-Crate metadata descriptor: recommended properties"
        ],
        expected_triggered_issues=[
            "about"
        ],
    )


def test_invalid_referenced_rocrate_missing_sddatepublished():
    """
    A referenced RO-Crate data entity whose @id is an absolute URI not declared
    as a persistent identifier SHOULD include `sdDatePublished`; omitting it
    triggers a RECOMMENDED warning (RO-Crate 1.2, § 4.5).
    """
    do_entity_test(
        __referenced_rocrate_crates__.invalid_missing_sddatepublished,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=[
            "Referenced RO-Crate: SHOULD have sdDatePublished when @id is an absolute URI without persistent identifier"
        ],
        expected_triggered_issues=[
            "SHOULD include `sdDatePublished` to indicate when the URI was accessed"
        ],
    )


def test_valid_referenced_rocrate_with_identifier():
    """
    A referenced RO-Crate with a declared `identifier` (case #1) does NOT
    require `sdDatePublished`; the structural SHACL check should NOT fire.
    """
    do_entity_test(
        __referenced_rocrate_crates__.valid_with_identifier,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_40.0", "ro-crate-1.2_45.1", "ro-crate-1.2_70.1", "ro-crate-1.2_73.1"],
    )


def test_valid_referenced_rocrate_with_relative_path():
    """
    A referenced RO-Crate with a relative path @id (case #2: attached nested
    sub-crate) does NOT require `sdDatePublished`; the structural SHACL check
    should NOT fire on relative path @ids.
    """
    do_entity_test(
        __referenced_rocrate_crates__.valid_with_relative_path,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=["ro-crate-1.2_40.0", "ro-crate-1.2_45.1", "ro-crate-1.2_70.1", "ro-crate-1.2_73.1"],
    )


def test_invalid_referenced_rocrate_no_cite_as_signposting(monkeypatch):
    """
    Python network-aware refinement: when the referenced RO-Crate @id does NOT
    declare Signposting `Link: rel="cite-as"`, `sdDatePublished` SHOULD be
    present.  Mocked HEAD response returns no `cite-as` link.
    """
    class _NoCiteAsResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}
        links = {}

        def raise_for_status(self):
            pass

    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _NoCiteAsResponse())

    do_entity_test(
        __referenced_rocrate_crates__.invalid_missing_sddatepublished,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        enforce_availability=True,
        expected_triggered_requirements=[
            "Referenced RO-Crate: Signposting cite-as refinement for sdDatePublished"
        ],
        expected_triggered_issues=[
            "has no Signposting `Link: rel=\"cite-as\"` declared"
        ],
    )


def test_valid_referenced_rocrate_with_cite_as_signposting(monkeypatch):
    """
    Python network-aware refinement: when the referenced RO-Crate @id DOES
    declare Signposting `Link: rel="cite-as"`, `sdDatePublished` is NOT
    required; the Python check suppresses its warning.  The structural SHACL
    warning still fires (it cannot inspect network headers).
    """
    class _CiteAsResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}
        links = {
            "cite-as": {
                "url": "https://doi.org/10.5281/zenodo.1234567",
                "rel": "cite-as",
            }
        }

        def raise_for_status(self):
            pass

    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _CiteAsResponse())

    # Python check passes (cite-as present); SHACL structural shape still
    # warns.  We verify the Python-specific requirement is NOT triggered.
    from rocrate_validator import services
    result = services.validate({
        "rocrate_uri": str(__referenced_rocrate_crates__.invalid_missing_sddatepublished),
        "profile_identifier": "ro-crate-1.2",
        "requirement_severity": models.Severity.RECOMMENDED,
        "enforce_availability": True,
    })
    failed_requirement_names = {
        issue.check.requirement.name for issue in result.get_issues()
    }
    assert (
        "Referenced RO-Crate: Signposting cite-as refinement for sdDatePublished"
        not in failed_requirement_names
    ), "Python cite-as refinement should NOT fire when cite-as is declared"
