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
from tests.ro_crates import WROCInvalidConformsTo_v1_1, WROCNoLicense_v1_1
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_wroc_rde_bad_conformsto():
    """
    Test a Workflow RO-Crate where the root data entity does not have a
    conformsTo that points to the WROC 1.1 profile.
    """
    do_entity_test(
        WROCInvalidConformsTo_v1_1().wroc_bad_conforms_to,
        Severity.RECOMMENDED,
        False,
        ["Root Data Entity Metadata"],
        ["The Root Data Entity conformsTo SHOULD be an array that contains at least https://w3id.org/workflowhub/workflow-ro-crate/1.1"],
        profile_identifier="workflow-ro-crate-1.1",
    )


def test_wroc_no_tests():
    """
    Test a Workflow RO-Crate with no test/ Dataset.
    """
    do_entity_test(
        WROCNoLicense_v1_1().wroc_no_license,
        Severity.OPTIONAL,
        False,
        ["test directory"],
        ["The test/ dir should be a Dataset"],
        profile_identifier="workflow-ro-crate-1.1",
    )


def test_wroc_no_examples():
    """
    Test a Workflow RO-Crate with no examples/ Dataset.
    """
    do_entity_test(
        WROCNoLicense_v1_1().wroc_no_license,
        Severity.OPTIONAL,
        False,
        ["examples directory"],
        ["The examples/ dir should be a Dataset"],
        profile_identifier="workflow-ro-crate-1.1",
    )
