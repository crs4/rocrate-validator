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

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidWTROC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_wtroc_testinstance_no_service():
    """\
    Test a Workflow Testing RO-Crate where a TestInstance does not refer to
    a TestService.
    """
    do_entity_test(
        InvalidWTROC().testinstance_no_service,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestInstance MUST"],
        ["The TestInstance MUST refer to a TestService via runsOn"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testinstance_no_url():
    """\
    Test a Workflow Testing RO-Crate where a TestInstance does not refer to
    the test service base URL.
    """
    do_entity_test(
        InvalidWTROC().testinstance_no_url,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestInstance MUST"],
        ["The TestInstance MUST refer to the test service base URL via url"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testinstance_no_resource():
    """\
    Test a Workflow Testing RO-Crate where a TestInstance does not refer to
    the relative URL of the test project via resource.
    """
    do_entity_test(
        InvalidWTROC().testinstance_no_resource,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestInstance MUST"],
        ["The TestInstance MUST refer to the relative URL of the test project via resource"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testinstance_bad_runson():
    """\
    Test a Workflow Testing RO-Crate where a TestInstance has a runsOn
    property that does not refer to a TestService.
    """
    do_entity_test(
        InvalidWTROC().testinstance_bad_runson,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestInstance MUST"],
        ["The TestInstance MUST refer to a TestService via runsOn"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testinstance_bad_url():
    """\
    Test a Workflow Testing RO-Crate where a TestInstance has a url
    property that does not refer to a string with a URL pattern.
    """
    do_entity_test(
        InvalidWTROC().testinstance_bad_url,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestInstance MUST"],
        ["The TestInstance MUST refer to the test service base URL via url"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testinstance_bad_resource():
    """\
    Test a Workflow Testing RO-Crate where a TestInstance has a resource
    property that does not refer to a string.
    """
    do_entity_test(
        InvalidWTROC().testinstance_bad_resource,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestInstance MUST"],
        ["The TestInstance MUST refer to the relative URL of the test project via resource"],
        profile_identifier="workflow-testing-ro-crate"
    )
