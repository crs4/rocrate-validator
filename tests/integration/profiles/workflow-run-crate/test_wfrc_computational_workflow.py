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


def test_wfrc_workflow_input_no_formalparam():
    """\
    Test a Workflow Run Crate where a ComputationalWorkflow input does not
    point to FormalParameter instances.
    """
    do_entity_test(
        InvalidWfRC().workflow_input_no_formalparam,
        Severity.REQUIRED,
        False,
        ["Workflow Run Crate ComputationalWorkflow MUST"],
        ["ComputationalWorkflow input and output MUST point to FormalParameter entities"],
        profile_identifier="workflow-run-crate"
    )


def test_wfrc_workflow_output_no_formalparam():
    """\
    Test a Workflow Run Crate where a ComputationalWorkflow output does not
    point to FormalParameter instances.
    """
    do_entity_test(
        InvalidWfRC().workflow_output_no_formalparam,
        Severity.REQUIRED,
        False,
        ["Workflow Run Crate ComputationalWorkflow MUST"],
        ["ComputationalWorkflow input and output MUST point to FormalParameter entities"],
        profile_identifier="workflow-run-crate"
    )


def test_wfrc_workflow_no_environment():
    """\
    Test a Workflow Run Crate where a ComputationalWorkflow does not
    have an environment.
    """
    do_entity_test(
        InvalidWfRC().workflow_no_environment,
        Severity.OPTIONAL,
        False,
        ["Workflow Run Crate ComputationalWorkflow MAY"],
        ["The Workflow MAY have an environment"],
        profile_identifier="workflow-run-crate"
    )


def test_wfrc_workflow_bad_environment():
    """\
    Test a Workflow Run Crate where a ComputationalWorkflow has an
    environment that does not point to FormalParameter entities.
    """
    do_entity_test(
        InvalidWfRC().workflow_bad_environment,
        Severity.OPTIONAL,
        False,
        ["Workflow Run Crate ComputationalWorkflow SHOULD"],
        ["If the Workflow has an environment, it SHOULD point to entities of type FormalParameter"],
        profile_identifier="workflow-run-crate"
    )
