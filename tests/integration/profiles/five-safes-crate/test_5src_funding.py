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
from tests.ro_crates import Invalid5sROC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_5src_funding_project_no_name():
    """\
    Test a Five Safes Crate where the funding Project does not have a name.
    """
    do_entity_test(
        rocrate_path=Invalid5sROC().funding_project_no_name,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Funding body Project"],
        expected_triggered_issues=[
            "The Project Entity MUST have a `name` property (as specified by schema.org)"
        ],
        profile_identifier="five-safes-crate",
    )
