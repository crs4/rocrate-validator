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


def test_wtroc_testsuite_not_mentioned():
    """\
    Test a Workflow Testing RO-Crate where a TestSuite is not listed in the
    Root Data Entity's mentions.
    """
    do_entity_test(
        InvalidWTROC().testsuite_not_mentioned,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestSuite MUST"],
        ["The TestSuite MUST be referenced from the Root Data Entity via mentions"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testsuite_no_instance_no_def():
    """\
    Test a Workflow Testing RO-Crate where a TestSuite does not refer to
    either a TestSuite or a TestDefinition.
    """
    do_entity_test(
        InvalidWTROC().testsuite_no_instance_no_def,
        Severity.REQUIRED,
        False,
        ["TestSuite instance or definition"],
        ["The TestSuite MUST refer to a TestInstance or TestDefinition"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testsuite_no_mainentity():
    """\
    Test a Workflow Testing RO-Crate where a TestSuite does not refer to
    the tested workflow via mainEntity.
    """
    do_entity_test(
        InvalidWTROC().testsuite_no_mainentity,
        Severity.RECOMMENDED,
        False,
        ["Workflow Testing RO-Crate TestSuite SHOULD"],
        ["The TestSuite SHOULD refer to the tested workflow via mainEntity"],
        profile_identifier="workflow-testing-ro-crate"
    )
