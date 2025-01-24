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
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import InvalidDataEntity
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


#  Global set up the paths
paths = InvalidDataEntity()


def test_missing_data_entity_reference():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.missing_hasPart_data_entity_reference,
        models.Severity.REQUIRED,
        False,
        ["Data Entity: REQUIRED properties"],
        ["sort-and-change-case.ga", "foo/xxx"]
    )


def test_data_entity_must_be_directly_linked():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.direct_hasPart_data_entity_reference,
        models.Severity.REQUIRED,
        True,
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER]
    )


def test_data_entity_must_be_indirectly_linked():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.indirect_hasPart_data_entity_reference,
        models.Severity.REQUIRED,
        True,
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER]
    )


def test_directory_data_entity_wo_trailing_slash():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.directory_data_entity_wo_trailing_slash,
        models.Severity.REQUIRED,
        False,
        ["Directory Data Entity: REQUIRED value restriction"],
        ["Every Data Entity Directory URI MUST end with `/`"]
    )


def test_missing_data_entity_encoding_format():
    """"""
    do_entity_test(
        paths.missing_data_entity_encoding_format,
        models.Severity.RECOMMENDED,
        False,
        ["File Data Entity: RECOMMENDED properties"],
        ["Missing or invalid `encodingFormat` linked to the `File Data Entity`"]
    )


def test_invalid_data_entity_encoding_format_pronom():
    """"""
    do_entity_test(
        paths.invalid_data_entity_encoding_format_pronom,
        models.Severity.RECOMMENDED,
        False,
        ["File Data Entity: RECOMMENDED properties"],
        ["Missing or invalid `encodingFormat` linked to the `File Data Entity`"]
    )


def test_invalid_data_entity_encoding_format_ctx_website_type():
    """"""
    do_entity_test(
        paths.invalid_encoding_format_ctx_entity_missing_ws_type,
        models.Severity.RECOMMENDED,
        False,
        ["File Data Entity: RECOMMENDED properties"],
        ["Missing or invalid `encodingFormat` linked to the `File Data Entity`"]
    )


def test_invalid_data_entity_encoding_format_ctx_website_name():
    """"""
    do_entity_test(
        paths.invalid_encoding_format_ctx_entity_missing_ws_name,
        models.Severity.RECOMMENDED,
        False,
        ["WebSite RECOMMENDED Properties"],
        ["A WebSite MUST have a `name` property"]
    )


def test_valid_data_entity_encoding_format_pronom():
    """"""
    do_entity_test(
        paths.valid_encoding_format_pronom,
        models.Severity.RECOMMENDED,
        True,
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER]
    )


def test_valid_data_entity_encoding_format_ctx_website():
    """"""
    do_entity_test(
        paths.valid_encoding_format_ctx_entity,
        models.Severity.RECOMMENDED,
        True,
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER]
    )
