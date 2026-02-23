# Copyright (c) 2024-2025 CRS4
# Copyright (c) 2025-2026 eScience Lab, The University of Manchester
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

# Dynamically fetch the SKIP_WEB_RESOURCE_AVAILABILITY_IDENTIFIER
# required as disable_inherited_profiles_reporting does not disable Python checks from
# inherited profiles (https://github.com/crs4/rocrate-validator/issues/135)
rocrate_profile = services.get_profile("ro-crate")
if not rocrate_profile:
    raise RuntimeError("Unable to load the RO-Crate profile")
check_local_data_entity_existence = rocrate_profile.get_requirement_check(
    "Web-based Data Entity: resource availability"
)
assert (
    check_local_data_entity_existence
), "Unable to find the requirement 'Web-based Data Entity: resource availability'"
SKIP_WEB_RESOURCE_AVAILABILITY_IDENTIFIER = check_local_data_entity_existence.identifier


def test_valid_five_safes_crate_request_required():
    """Test a valid Five Safes Crate representing a request."""
    do_entity_test(
        ValidROC().five_safes_crate_request,
        Severity.REQUIRED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[
            SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
        ],
    )


@pytest.mark.xfail(
    reason="""
        Checks that ensure certain Five Safes actions are present currently fail for this crate,
        as this crate represents an early stage of a process before those actions have happened.
    """
)
def test_valid_five_safes_crate_request_recommended():
    """Test a valid Five Safes Crate representing a request."""
    do_entity_test(
        ValidROC().five_safes_crate_request,
        Severity.RECOMMENDED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[
            SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
            SKIP_WEB_RESOURCE_AVAILABILITY_IDENTIFIER,
        ],
        disable_inherited_profiles_issue_reporting=True,
    )


def test_valid_five_safes_crate_result_required():
    """Test a valid Five Safes Crate representing a result."""
    do_entity_test(
        ValidROC().five_safes_crate_result,
        Severity.REQUIRED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[
            SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
        ],
    )


def test_valid_five_safes_crate_result_recommended():
    """Test a valid Five Safes Crate representing a result."""
    do_entity_test(
        ValidROC().five_safes_crate_result,
        Severity.RECOMMENDED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[
            SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
            SKIP_WEB_RESOURCE_AVAILABILITY_IDENTIFIER,
        ],
        disable_inherited_profiles_reporting=True,
    )


def test_valid_five_safes_crate_multiple_context():
    """Test a valid Five Safes Crate representing a result."""
    do_entity_test(
        ValidROC().five_safes_crate_multiple_context,
        Severity.REQUIRED,
        True,
        profile_identifier="five-safes-crate",
        skip_checks=[
            SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
        ],
    )
