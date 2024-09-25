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
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_valid_roc_required():
    """Test a valid RO-Crate."""
    do_entity_test(
        ValidROC().wrroc_paper,
        Severity.REQUIRED,
        True
    )


def test_valid_roc_recommended():
    """Test a valid RO-Crate."""
    do_entity_test(
        ValidROC().wrroc_paper,
        Severity.RECOMMENDED,
        True
    )


def test_valid_roc_required_with_long_datetime():
    """Test a valid RO-Crate."""
    do_entity_test(
        ValidROC().wrroc_paper_long_date,
        Severity.REQUIRED,
        True
    )
