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


def test_formalparam_no_inv_exampleofwork():
    """\
    Test a Workflow Run Crate where a FormalParameter is not referenced via
    exampleOfWork.
    """
    do_entity_test(
        InvalidWfRC().formalparam_no_inv_exampleofwork,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter SHOULD"],
        ["FormalParameter SHOULD be referenced from a data entity or PropertyValue via exampleOfWork"],
        profile_identifier="workflow-run-crate"
    )


# # This currently does not pass
#
# def test_formalparam_bad_inv_exampleofwork():
#     """\
#     Test a Workflow Run Crate where a FormalParameter is referenced via
#     exampleOfWork by an entity that is not a data entity or PropertyValue.
#     """
#     do_entity_test(
#         InvalidWfRC().formalparam_bad_inv_exampleofwork,
#         Severity.RECOMMENDED,
#         False,
#         ["Workflow Run Crate FormalParameter SHOULD"],
#         ["FormalParameter SHOULD be referenced from a data entity or PropertyValue via exampleOfWork"],
#         profile_identifier="workflow-run-crate"
#     )
