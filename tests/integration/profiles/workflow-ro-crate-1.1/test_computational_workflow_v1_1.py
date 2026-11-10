# Copyright (c) 2024-2026 CRS4
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
from tests.ro_crates import WROCInvalidComputationalWorkflow_v1_1
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_computational_workflow_no_input():
    """
    Test a Workflow RO-Crate where a computational workflow does not have
    an input property.
    """
    do_entity_test(
        WROCInvalidComputationalWorkflow_v1_1().no_input,
        Severity.OPTIONAL,
        False,
        ["Workflow RO-Crate ComputationalWorkflow MAY"],
        ["A ComputationalWorkflow MAY have an input"],
        profile_identifier="workflow-ro-crate-1.1",
    )


def test_computational_workflow_no_output():
    """
    Test a Workflow RO-Crate where a computational workflow does not have
    an output property.
    """
    do_entity_test(
        WROCInvalidComputationalWorkflow_v1_1().no_output,
        Severity.OPTIONAL,
        False,
        ["Workflow RO-Crate ComputationalWorkflow MAY"],
        ["A ComputationalWorkflow MAY have an output"],
        profile_identifier="workflow-ro-crate-1.1",
    )


def test_computational_workflow_bad_input():
    """
    Test a Workflow RO-Crate where a computational workflow has an input
    property that does not point to a FormalParameter.
    """
    do_entity_test(
        WROCInvalidComputationalWorkflow_v1_1().bad_input,
        Severity.REQUIRED,
        False,
        ["Workflow RO-Crate ComputationalWorkflow MUST"],
        ["ComputationalWorkflow input and output MUST point to FormalParameter entities"],
        profile_identifier="workflow-ro-crate-1.1",
    )


def test_computational_workflow_bad_output():
    """
    Test a Workflow RO-Crate where a computational workflow has an output
    property that does not point to a FormalParameter.
    """
    do_entity_test(
        WROCInvalidComputationalWorkflow_v1_1().bad_output,
        Severity.REQUIRED,
        False,
        ["Workflow RO-Crate ComputationalWorkflow MUST"],
        ["ComputationalWorkflow input and output MUST point to FormalParameter entities"],
        profile_identifier="workflow-ro-crate-1.1",
    )
