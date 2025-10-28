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


def test_5src_agent_memberOf_not_project():
    """
    Test a Five Safes Crate where an agent's `memberOf` does NOT reference a schema:Project.
    (We replace the referenced Project with a plain literal.)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?agent schema:memberOf ?org .
        }
        INSERT {
            ?agent schema:memberOf "Not a project (literal replacement)"
        }
        WHERE {
            ?action a schema:CreateAction ;
            schema:agent ?agent .
            ?agent schema:memberOf ?org .
            ?org a schema:Project .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Requesting Agent"],
        expected_triggered_issues=[
            "The 'memberOf' property of an agent MUST be of type Project."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_agent_memberOf_project_not_in_root():
    """
    Test a Five Safes Crate where NONE of the Projects referenced by Agent->memberOf are included
    in the set of Projects referenced by RootDataEntity->sourceOrganization.
    (We replace an agent's memberOf with a new Project that the root does not reference.)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?agent schema:memberOf ?org .
        }
        INSERT {
            # assign the agent to a new Project that is not referenced by the Root Data Entity
            ?agent schema:memberOf <./missing-project> .
            <./missing-project> a schema:Project .
        }
        WHERE {
            # locate a CreateAction -> agent -> memberOf that currently points to a Project
            ?action a schema:CreateAction ;
                    schema:agent ?agent .

            ?agent schema:memberOf ?org .
            ?org a schema:Project .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Agent Project Intersection"],
        expected_triggered_issues=[
            """Agent -> memberOf MUST intersect RootDataEntity -> sourceOrganization."""
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD warns tests
def test_5src_agent_memberOf_missing_warning():
    """
    Test a Five Safes Crate where the Requesting Agent does NOT have the 'memberOf' property.
    This should trigger the SHACL warning: the Requesting Agent SHOULD have a `memberOf` property.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?agent schema:memberOf ?org .
        }
        WHERE {
            ?action a schema:CreateAction ;
                    schema:agent ?agent .
            ?agent schema:memberOf ?org .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,  # or True if warnings are not treated as failures
        expected_triggered_requirements=["Requesting Agent"],
        expected_triggered_issues=[
            "The Requesting Agent SHOULD have a `memberOf` property."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
