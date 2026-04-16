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
from tests.ro_crates import InvalidROCrate12, ValidROCrate12
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


paths = InvalidROCrate12()
valid = ValidROCrate12()


def test_valid_attached_ro_crate_1_2():
    do_entity_test(
        valid.attached,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_valid_attached_ro_crate_absolute_root_id():
    do_entity_test(
        valid.attached_absolute_root,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_context_version():
    do_entity_test(
        paths.invalid_context,
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ["does not reference the required context"],
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_date_published_single_value():
    do_entity_test(
        paths.invalid_date_published,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Root Data Entity REQUIRED properties"],
        profile_identifier="ro-crate-1.2",
    )


def test_valid_detached_ro_crate():
    do_entity_test(
        valid.detached,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_valid_detached_prefixed_metadata_filename():
    do_entity_test(
        valid.detached_prefixed,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_detached_relative_entity():
    do_entity_test(
        paths.detached_relative_entity,
        models.Severity.REQUIRED,
        False,
        ["Detached RO-Crate: data entities MUST be web-based"],
        profile_identifier="ro-crate-1.2",
    )


def test_detached_bad_filename_recommended():
    do_entity_test(
        paths.detached_bad_filename,
        models.Severity.RECOMMENDED,
        False,
        ["File Descriptor naming convention"],
        ["metadata descriptor filename"],
        profile_identifier="ro-crate-1.2",
    )
