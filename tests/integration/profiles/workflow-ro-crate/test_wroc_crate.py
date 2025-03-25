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

from rocrate_validator.models import Severity
from tests.ro_crates import WROCNoLicense
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_wroc_no_tests():
    """\
    Test a Workflow RO-Crate with no test/ Dataset.
    """
    do_entity_test(
        WROCNoLicense().wroc_no_license,
        Severity.OPTIONAL,
        False,
        ["test directory"],
        ["The test/ dir should be a Dataset"],
        profile_identifier="workflow-ro-crate"
    )


def test_wroc_no_examples():
    """\
    Test a Workflow RO-Crate with no examples/ Dataset.
    """
    do_entity_test(
        WROCNoLicense().wroc_no_license,
        Severity.OPTIONAL,
        False,
        ["examples directory"],
        ["The examples/ dir should be a Dataset"],
        profile_identifier="workflow-ro-crate"
    )
