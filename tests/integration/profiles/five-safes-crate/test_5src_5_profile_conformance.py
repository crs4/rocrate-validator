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


# ----- SHOULD fails tests


def test_5src_root_data_entity_missing_conformsto_property():
    """
    Test a Five Safes Crate where the RootDataEntity does not have the conformsTo property.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?rootdataentity dct:conformsTo ?profile .
        }
        WHERE {
            ?metadatafile a schema:CreativeWork ;
                          schema:about ?rootdataentity .
            ?rootdataentity dct:conformsTo ?profile .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "Root Dataset SHOULD include `conformsTo` https://w3id.org/5s-crate/0.4"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_root_data_entity_conforms_to_wrong_profile():
    """
    Test a Five Safes Crate where the RootDataEntity does not conform to the expected profile.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?rootdataentity dct:conformsTo ?profile .
        }
        INSERT {
            ?rootdataentity dct:conformsTo "This is not the IRI to the 5sc profile"
        }
        WHERE {
            ?metadatafile a schema:CreativeWork ;
                          schema:about ?rootdataentity .
            ?rootdataentity dct:conformsTo ?profile .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "Root Dataset SHOULD include `conformsTo` https://w3id.org/5s-crate/0.4"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_root_data_entity_has_publisher_but_not_date_published():
    """
    Test a Five Safes Crate where the RootDataEntity has published but not date published.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?rootdataentity schema:datePublished ?datePublished .
        }
        WHERE {
            ?metadatafile a schema:CreativeWork ;
                          schema:about ?rootdataentity .
            ?rootdataentity schema:publisher ?publisher ;
                            schema:datePublished ?datePublished .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["datePublished present on published crates"],
        expected_triggered_issues=[
            "Published crates SHOULD include schema:datePublished."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_root_data_entity_has_publisher_but_not_license():
    """
    Test a Five Safes Crate where the RootDataEntity has publisher but not license.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?rootdataentity schema:license ?license .
        }
        WHERE {
            ?metadatafile a schema:CreativeWork ;
                          schema:about ?rootdataentity .
            ?rootdataentity schema:publisher ?publisher ;
                            schema:license ?license .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["License present on published crates"],
        expected_triggered_issues=[
            "Profile Conformance: Published crates SHOULD include a license."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- MAY fails tests
