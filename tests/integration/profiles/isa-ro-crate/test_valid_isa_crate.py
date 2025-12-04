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
from tests.ro_crates import ValidROC,InvalidISARC
from tests.shared import do_entity_test
import pytest

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# @pytest.mark.xfail(
#     reason="'File Descriptor JSON-LD format' check fails: The 17 occurrences of the JSON-LD key 'columnIndex' are not "
#     "allowed in the compacted format because it is not present in the @context of the document"
# )
def test_valid_isa_ro_crate():
    """Test a valid ISA RO-Crate."""
    do_entity_test(
        ValidROC().isa_ro_crate,
        # InvalidISARC().process_is_missing_objects,
        Severity.REQUIRED,
        True,
        profile_identifier="isa-ro-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
    )
