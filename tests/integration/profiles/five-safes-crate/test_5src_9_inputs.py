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


# ----- SHOULD fails tests


def test_input_does_not_reference_formalparameter():
    """
    Test a Five Safes Crate where an input entity does not reference a
    `bioschemas:FormalParameter using `schema:exampleOfWork`.
    (We replace tjhe ?object of input --> exampleOfWork  with a literal)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?input schema:exampleOfWork ?formalParameter .
        }
        INSERT {
            ?input schema:exampleOfWork "not-a-formal-parameter" .
        }
        WHERE {
            ?input schema:exampleOfWork ?formalParameter .
            ?formalParameter a bioschemas:FormalParameter .
            ?action a schema:CreateAction ;
                    schema:object ?input .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Input"],
        expected_triggered_issues=[
            "Input SHOULD reference a FormalParameter using exampleOfWork"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
