# Copyright (c) 2024 DataPLANT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC, InvalidISARC
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
