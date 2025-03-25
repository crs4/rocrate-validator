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
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_valid_process_run_crate_required():
    """Test a valid Process Run Crate."""
    do_entity_test(
        ValidROC().process_run_crate,
        Severity.REQUIRED,
        True,
        profile_identifier="process-run-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER]
    )
    do_entity_test(
        ValidROC().process_run_crate_collections,
        Severity.REQUIRED,
        True,
        profile_identifier="process-run-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER]
    )
    do_entity_test(
        ValidROC().process_run_crate_containerimage,
        Severity.REQUIRED,
        True,
        profile_identifier="process-run-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER]
    )
