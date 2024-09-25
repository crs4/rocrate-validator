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

import pytest

from rocrate_validator import models
from tests.ro_crates import InvalidFileDescriptorEntity
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)

#  Global set up the paths
paths = InvalidFileDescriptorEntity()


def test_missing_entity():
    """Test a RO-Crate without a file descriptor entity."""
    do_entity_test(
        paths.missing_entity,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Metadata File Descriptor entity existence"],
        ["The root of the document MUST have an entity with @id `ro-crate-metadata.json`"]
    )


def test_invalid_entity_type():
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.invalid_entity_type,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Metadata File Descriptor REQUIRED properties"],
        ["The RO-Crate metadata file MUST be a CreativeWork, as per schema.org"]
    )


def test_missing_entity_about():
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.missing_entity_about,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Metadata File Descriptor REQUIRED properties"],
        ["The RO-Crate metadata file MUST be a CreativeWork, as per schema.org",
         "The RO-Crate metadata file descriptor MUST have an `about` property referencing the Root Data Entity"]
    )


@pytest.mark.skip(reason="This test is not working as expected")
def test_invalid_entity_about():
    """Test a RO-Crate with an invalid about property in the file descriptor."""
    do_entity_test(
        paths.invalid_entity_about,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Metadata File Descriptor REQUIRED properties"],
        ["The RO-Crate metadata file descriptor MUST have an `about` property referencing the Root Data Entity"]
    )


def test_invalid_entity_about_type():
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.invalid_entity_about_type,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Metadata File Descriptor REQUIRED properties"],
        ["The RO-Crate metadata file descriptor MUST have an `about` property referencing the Root Data Entity"]
    )


def test_missing_conforms_to():
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.missing_conforms_to,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Metadata File Descriptor REQUIRED properties"],
        ["The RO-Crate metadata file descriptor MUST have a `conformsTo` "
         "property with the RO-Crate specification version"]
    )


def test_invalid_conforms_to():
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.invalid_conforms_to,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Metadata File Descriptor REQUIRED properties"],
        ["The RO-Crate metadata file descriptor MUST have a `conformsTo` "
         "property with the RO-Crate specification version"]
    )
