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
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test, SPARQL_PREFIXES

# set up logging
logger = logging.getLogger(__name__)


# ---- MUST fails tests


def test_5src_no_signoff_phase():
    """
    Test a Five Safes Crate where no Sign-Off phase is listed.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> ?p ?o .
            <./> schema:mentions <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> .
        }
        WHERE {
            OPTIONAL { <./> schema:mentions <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> . }
            OPTIONAL { <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> ?p ?o . }
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhase"],
        expected_triggered_issues=[
            "There SHOULD be a Sign-Off Phase in the Final RO-Crate"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


