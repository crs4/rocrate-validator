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
from tests.ro_crates import ValidWROC_v1_1
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_valid_workflow_roc_required():
    """Test valid Workflow RO-Crate metadata without checking the payload."""
    do_entity_test(
        ValidWROC_v1_1().workflow_roc_v1_1,
        Severity.REQUIRED,
        True,
        profile_identifier="workflow-ro-crate-1.1",
        metadata_only=True,
    )
