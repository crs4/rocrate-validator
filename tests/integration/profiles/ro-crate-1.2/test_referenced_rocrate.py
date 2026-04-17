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
from tests.ro_crates_1_2 import ReferencedROCrates
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
        skip_checks=["ro-crate-1.2_40.0", "ro-crate-1.2_44.1", "ro-crate-1.2_70.1", "ro-crate-1.2_69.1"],
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
