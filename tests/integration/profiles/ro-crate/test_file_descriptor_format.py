# Copyright (c) 2024 CRS4
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
from tests.ro_crates import InvalidFileDescriptor
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


#  Global set up the paths
paths = InvalidFileDescriptor()


def test_missing_file_descriptor():
    """Test a RO-Crate without a file descriptor."""
    with paths.missing_file_descriptor as rocrate_path:
        do_entity_test(
            rocrate_path,
            models.Severity.REQUIRED,
            False,
            ["File Descriptor existence"],
            []
        )


def test_not_valid_json_format():
    """Test a RO-Crate with an invalid JSON file descriptor format."""
    do_entity_test(
        paths.invalid_json_format,
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON format"],
        []
    )


def test_not_valid_jsonld_format_missing_context():
    """Test a RO-Crate with an invalid JSON-LD file descriptor format."""
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_context",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        []
    )


def test_not_valid_jsonld_format_not_flattened():
    """Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor are not flattened.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/not_flattened",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ["RO-Crate file descriptor \"ro-crate-metadata.json\" is not fully flattened"]
    )


def test_not_valid_jsonld_format_missing_ids():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @id attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_id",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ["file descriptor does not contain the @id attribute"]
    )


def test_not_valid_jsonld_format_missing_types():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @type attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_type",
        models.Severity.REQUIRED,
        False,
        ["File Descriptor JSON-LD format"],
        ["file descriptor does not contain the @type attribute"]
    )
