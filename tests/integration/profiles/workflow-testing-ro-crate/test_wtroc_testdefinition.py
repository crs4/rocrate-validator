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


def test_wtroc_testdefinition_bad_type():
    """\
    Test a Workflow Testing RO-Crate where a TestDefinition does not have the
    File (MediaObject) and TestDefinition types.
    """
    do_entity_test(
        InvalidWTROC().testdefinition_bad_type,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestDefinition MUST"],
        ["The TestDefinition MUST have types TestDefinition and File"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testdefinition_no_engine():
    """\
    Test a Workflow Testing RO-Crate where a TestDefinition does not refer
    to the test engine SoftwareApplication via conformsTo.
    """
    do_entity_test(
        InvalidWTROC().testdefinition_no_engine,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestDefinition MUST"],
        ["The TestDefinition MUST refer to the test engine it is written for via conformsTo"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testdefinition_no_engineversion():
    """\
    Test a Workflow Testing RO-Crate where a TestDefinition does not refer
    to the test engine's version via engineVersion.
    """
    do_entity_test(
        InvalidWTROC().testdefinition_no_engineversion,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestDefinition MUST"],
        ["The TestDefinition MUST refer to the test engine version via engineVersion"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testdefinition_bad_conformsto():
    """\
    Test a Workflow Testing RO-Crate where a TestDefinition does not refer
    to the test engine SoftwareApplication via conformsTo.
    """
    do_entity_test(
        InvalidWTROC().testdefinition_bad_conformsto,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestDefinition MUST"],
        ["The TestDefinition MUST refer to the test engine it is written for via conformsTo"],
        profile_identifier="workflow-testing-ro-crate"
    )


def test_wtroc_testdefinition_bad_engineversion():
    """\
    Test a Workflow Testing RO-Crate where a TestDefinition does not refer
    to the test engine's version as a string.
    """
    do_entity_test(
        InvalidWTROC().testdefinition_bad_engineversion,
        Severity.REQUIRED,
        False,
        ["Workflow Testing RO-Crate TestDefinition MUST"],
        ["The TestDefinition MUST refer to the test engine version via engineVersion"],
        profile_identifier="workflow-testing-ro-crate"
    )
