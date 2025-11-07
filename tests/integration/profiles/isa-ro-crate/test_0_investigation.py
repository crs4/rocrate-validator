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


# ----- MUST fails tests


def test_isa_additionaltype_not_investigation():
    """
    Test an ISA RO-Crate where no Dataset has `additionalType` of "Investigation".
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:additionalType "Investigation" .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Investigation" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Root Data Entity must be Investigation"],
        expected_triggered_issues=[
            "The root data entity must have additionalType of `Investigation`"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
