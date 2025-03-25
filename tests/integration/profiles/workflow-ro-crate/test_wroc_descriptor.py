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
from tests.ro_crates import WROCInvalidConformsTo
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_wroc_descriptor_bad_conforms_to():
    """\
    Test a Workflow RO-Crate where the metadata file descriptor does not
    contain the required URIs.
    """
    do_entity_test(
        WROCInvalidConformsTo().wroc_descriptor_bad_conforms_to,
        Severity.RECOMMENDED,
        False,
        ["WROC Metadata File Descriptor properties"],
        ["The Metadata File Descriptor conformsTo SHOULD contain https://w3id.org/ro/crate/1.1 "
         "and https://w3id.org/workflowhub/workflow-ro-crate/1.0"],
        profile_identifier="workflow-ro-crate"
    )
