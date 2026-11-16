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
from tests.ro_crates import ValidProvRC_v0_6
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_valid_provenance_run_crate_v0_6_required():
    """Test a valid Provenance Run Crate 0.6."""
    do_entity_test(
        ValidProvRC_v0_6().provenance_run_crate_v0_6,
        Severity.REQUIRED,
        True,
        profile_identifier="provenance-run-crate-0.6",
        metadata_only=True,
    )
