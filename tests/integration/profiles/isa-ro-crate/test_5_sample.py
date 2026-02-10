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
        rocrate_path=ValidROC().isa_ro_crate_manual,
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Sample additional property MUST be of type PropertyValue"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
