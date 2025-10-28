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


def test_5src_root_data_entity_without_source_organization():
    """
    Test a Five Safes Crate where the Root Data Entity does NOT have the 'sourceOrganization' property.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:sourceOrganization ?o .
        }
        WHERE {
            <./> schema:sourceOrganization ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            """The Root Data Entity MUST have a `sourceOrganization` property."""
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_root_data_entity_source_organization_not_organization():
    """
    Test a Five Safes Crate where the Root Data Entity's `sourceOrganization` property
    does NOT reference a `schema:Project` entity.
    (We replace any existing sourceOrganization with a literal to violate the class constraint.)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:sourceOrganization ?o .
        }
        INSERT {
            # insert a literal instead of an IRI
            <./> schema:sourceOrganization "Investigation of cancer (TRE72 project 81)" .
        }
        WHERE {
            <./> schema:sourceOrganization ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            """The `sourceOrganization` property of the RootDataEntity MUST point to a Project entity."""
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
