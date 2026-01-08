# Copyright (c) 2024-2025 CRS4
# Copyright (c) 2025-2026 eScience Lab, The University of Manchester
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


def test_completed_createaction_does_not_have_result():
    """
    Test a Five Safes Crate where `CreateAction` has `CompletedActionStatus` but
    does not have the property `result`.
    (We remove `result` from `CreateAction` if this has `CompletedActionStatus`)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action schema:result ?o .
        }
        WHERE {
            ?action a schema:CreateAction ;
                      schema:actionStatus "http://schema.org/CompletedActionStatus" ;
                      schema:result ?o
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=[
            "`CreateAction` with CompletedActionStatus SHOULD have the `schema:result` property."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_result_output_does_not_have_allowed_type():
    """
    Test a Five Safes Crate where the result output does not have a type that
    is among those allowed.
    (We remove the output entity and replace it with one that is of a wrong type)"""
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?result a ?oldType .
        }
        INSERT {
            ?result a schema:Person .
        }
        WHERE {
            ?action a schema:CreateAction ;
                    schema:result ?result .
            ?result a ?oldType .
            }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Output"],
        expected_triggered_issues=[
            "Result SHOULD have a `@type` among an allowed set of values."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
