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


def test_5src_responsible_project_funding_not_grant():
    """
    Test a Five Safes Crate where a Responsible Project's `funding` property
    is NOT of type schema:Grant.
    (We replace the funding reference with a literal.)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?project schema:funding ?grant .
        }
        INSERT {
            ?project schema:funding "Not a grant (literal replacement)" .
        }
        WHERE {
            ?action a schema:CreateAction ;
                    schema:agent ?agent .
            ?agent schema:memberOf ?project .
            ?project schema:funding ?grant .
            ?grant a schema:Grant .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Responsible Project"],
        expected_triggered_issues=[
            "The property 'funding' of the Responsible Project MUST be of type schema:Grant."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_responsible_project_member_not_organization():
    """
    Test a Five Safes Crate where a Responsible Project's `member` property
    is NOT of type schema:Organization.
    (We replace the member reference with a literal.)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?project schema:member ?org .
        }
        INSERT {
            ?project schema:member "Not an organization (literal replacement)" .
        }
        WHERE {
            ?action a schema:CreateAction ;
                    schema:agent ?agent .
            ?agent schema:memberOf ?project .
            ?project schema:member ?org .
            ?org a schema:Organization .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Responsible Project"],
        expected_triggered_issues=[
            "The property 'member' of the Responsible Project MUST be of type schema:Organization."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ---- MAY warns tests


def test_5src_responsible_project_missing_funding_property():
    """
    Test a Five Safes Crate where a Responsible Project does NOT have the `funding` property.
    This should trigger the SHACL info: 'The Responsible Project does not have the property `funding`.'
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?project schema:funding ?f .
        }
        WHERE {
            ?action a schema:CreateAction ;
                    schema:agent ?agent .
            ?agent schema:memberOf ?project .
            ?project schema:funding ?f .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,  # or True if Info is not treated as failure
        expected_triggered_requirements=["Responsible Project"],
        expected_triggered_issues=[
            "The Responsible Project does not have the property `funding`."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_responsible_project_missing_member_property():
    """
    Test a Five Safes Crate where a Responsible Project does NOT have the `member` property.
    This should trigger the SHACL info: 'The Responsible Project does not have the property `member`.'
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?project schema:member ?m .
        }
        WHERE {
            ?action a schema:CreateAction ;
                    schema:agent ?agent .
            ?agent schema:memberOf ?project .
            ?project schema:member ?m .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,  # or True if Info is treated as failure
        expected_triggered_requirements=["Responsible Project"],
        expected_triggered_issues=[
            "The Responsible Project does not have the property `member`."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
