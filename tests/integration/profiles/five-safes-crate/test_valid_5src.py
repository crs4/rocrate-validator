# Copyright (c) 2024-2025 CRS4
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

from rocrate_validator import services
from rocrate_validator.models import Severity
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.fixture
def skip_spec_version_identifier():
    """Returns identifiers for RO-Crate version checks in the base RO-Crate profile.

    Used to skip version checks while there is not a base profile available for RO-Crate 1.2 (only 1.1)
    """
    rocrate_profile = services.get_profile("ro-crate")
    if not rocrate_profile:
        raise RuntimeError("Unable to load the RO-Crate profile")
    check_conformsTo_version = \
        rocrate_profile.get_requirement_check("Metadata File Descriptor entity: `conformsTo` property")
    assert check_conformsTo_version, \
        'Unable to find the requirement "Metadata File Descriptor entity: `conformsTo` property"'
    SKIP_CONFORMSTO_VERSION_CHECK_IDENTIFIER = check_conformsTo_version.identifier
    return SKIP_CONFORMSTO_VERSION_CHECK_IDENTIFIER


def test_valid_five_safes_crate_request_required(skip_spec_version_identifier):
    """Test a valid Five Safes Crate representing a request."""
    do_entity_test(
        ValidROC().five_safes_crate_request,
        Severity.REQUIRED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[ SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER, skip_spec_version_identifier],
    )


def test_valid_five_safes_crate_result_required(skip_spec_version_identifier):
    """Test a valid Five Safes Crate representing a result."""
    do_entity_test(
        ValidROC().five_safes_crate_result,
        Severity.REQUIRED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER, skip_spec_version_identifier],
    )

def test_valid_five_safes_crate_multiple_context(skip_spec_version_identifier):
    """Test a valid Five Safes Crate representing a result."""
    do_entity_test(
        ValidROC().five_safes_crate_multiple_context,
        Severity.REQUIRED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER, skip_spec_version_identifier],
    )
