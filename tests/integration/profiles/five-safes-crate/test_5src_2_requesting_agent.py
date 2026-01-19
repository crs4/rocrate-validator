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


# ----- MUST fails tests


def test_createaction_does_not_have_agent():
    """
    Test a Five Safes Crate where CreateAction does not have the property agent.
    (We remove the property agent from the CreateAction entity)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action schema:agent ?agent .
        }
        WHERE {
            ?action schema:agent ?agent ;
                    a schema:CreateAction .
            ?agent a schema:Person .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=[
            "CreateAction MUST have at least one agent that is a contextual entity."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_createaction_agent_is_not_person():
    """
    Test a Five Safes Crate where CreateAction has an agent that is not of type schema:Person.
    (We replace the CreateAction's agent with an entity that has no type).
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action schema:agent ?agent .
        }
        INSERT {
            ?action schema:agent <#not-a-person> .
        }
        WHERE {
            ?action schema:agent ?agent ;
                    a schema:CreateAction .
            ?agent a schema:Person .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=["Each CreateAction agent MUST be typed as Person."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_agent_affiliation_not_organization():
    """
    Test a Five Safes Crate where the agent of CreateAction has an affiliation
    that is not of type schema:Organization.
    (We rereplace the agent's affiliation with an entity that has no type)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?agent schema:affiliation ?aff .
        }
        INSERT {
            ?agent schema:affiliation <#not-an-organization> .
        }
        WHERE {
            ?agent schema:affiliation ?aff ;
                    a schema:Person .
            ?aff a schema:Organization .
            ?action a schema:CreateAction ;
                    schema:agent ?agent .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=[
            "The affiliation of a CreateAction's agent MUST be a contextual entity with type Organization."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD warning tests


def test_5src_agent_does_not_have_affiliation():
    """
    Test a Five Safes Crate where the agent of CreteAction does not have an affiliatin.
    (We remove the triplet ?agent schema:affiliation ?org from the RO-Crate graph)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?agent schema:affiliation ?org .
        }
        WHERE {
            ?agent schema:affiliation ?org ;
                    a schema:Person .
            ?action a schema:CreateAction ;
                    schema:agent ?agent .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Agent of CreateAction"],
        expected_triggered_issues=[
            "The agent of a CreateAction entity SHOULD have an affiliation"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
