# Copyright (c) 2026 DataPLANT
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
def test_isa_property_value_name():
    """
    Test an ISA RO-Crate where a property value has no name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?property_value schema:name ?name .
        }
        WHERE {
            ?property_value a schema:PropertyValue .
            ?property_value schema:name "MyParameter" .
            ?property_value schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "PropertyValue entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_property_value_name_of_incorrect_type():
    """
    Test an ISA RO-Crate where a property value name has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?property_value schema:name ?name .
        }
        INSERT {
            ?property_value schema:name 42 .
        }
        WHERE {
            ?property_value a schema:PropertyValue .
            ?property_value schema:name "MyParameter" .
            ?property_value schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "PropertyValue entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_property_value_value():
    """
    Test an ISA RO-Crate where a property value has no value.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?property_value schema:value ?value .
        }
        WHERE {
            ?property_value a schema:PropertyValue .
            ?property_value schema:name "MyParameter" .
            ?property_value schema:value ?value .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "PropertyValue entity SHOULD have at least one value"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_property_value_value_of_incorrect_type():
    """
    Test an ISA RO-Crate where a property value value has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?property_value schema:value ?value .
        }
        INSERT {
            ?property_value schema:value ?term .
        }
        WHERE {
            ?property_value a schema:PropertyValue .
            ?property_value schema:name "MyParameter" .
            ?property_value schema:value ?value .
            ?term a schema:DefinedTerm .
            ?term schema:name "MyTerm" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "PropertyValue value MUST be of type string, float, or integer"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
