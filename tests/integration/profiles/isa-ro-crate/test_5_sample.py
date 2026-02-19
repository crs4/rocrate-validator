# Copyright (c) 2026 DataPLANT
# Copyright (c) 2026 The University of Manchester
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
def test_isa_sample_name():
    """
    Test an ISA RO-Crate where a sample has no name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?sample schema:name "MyInputSample" .
        }
        WHERE {
            ?sample a bioschemas:Sample .
            ?sample schema:name "MyInputSample" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Sample entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_sample_name_of_incorrect_type():
    """
    Test an ISA RO-Crate where a sample name has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?sample schema:name "MyInputSample" .
        }
        INSERT {
            ?sample schema:name 42 .
        }
        WHERE {
            ?sample a bioschemas:Sample .
            ?sample schema:name "MyInputSample" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Sample entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_sample_no_additional_property():
    """
    Test an ISA RO-Crate where a sample has no additional properties.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?sample bioschemas-prop:additionalProperty ?ap .
        }
        WHERE {
            ?sample a bioschemas:Sample .
            ?sample schema:name "MyInputSample" .
            ?sample bioschemas-prop:additionalProperty ?ap .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Sample entity SHOULD have at least one additional property"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_sample_additional_property_of_incorrect_type():
    """
    Test an ISA RO-Crate where a sample has additional property with wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?sample bioschemas-prop:additionalProperty ?ap .
        }
        INSERT {
            ?sample bioschemas-prop:additionalProperty 42 .
        }
        WHERE {
            ?sample a bioschemas:Sample .
            ?sample schema:name "MyInputSample" .
            ?sample bioschemas-prop:additionalProperty ?ap .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Sample additional property MUST be of type PropertyValue"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
