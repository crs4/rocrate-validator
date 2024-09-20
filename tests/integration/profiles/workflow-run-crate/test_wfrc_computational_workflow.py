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
from tests.ro_crates import InvalidWfRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_wfrc_workflow_no_input():
    """\
    Test a Workflow Run Crate where a ComputationalWorkflow has no input.
    """
    do_entity_test(
        InvalidWfRC().workflow_no_input,
        Severity.OPTIONAL,
        False,
        ["Workflow Run Crate ComputationalWorkflow MAY"],
        ["A ComputationalWorkflow MAY have an input"],
        profile_identifier="workflow-run-crate"
    )


def test_wfrc_workflow_no_output():
    """\
    Test a Workflow Run Crate where a ComputationalWorkflow has no output.
    """
    do_entity_test(
        InvalidWfRC().workflow_no_output,
        Severity.OPTIONAL,
        False,
        ["Workflow Run Crate ComputationalWorkflow MAY"],
        ["A ComputationalWorkflow MAY have an output"],
        profile_identifier="workflow-run-crate"
    )
