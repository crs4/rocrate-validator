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
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test, SPARQL_PREFIXES

# set up logging
logger = logging.getLogger(__name__)


# ----- MUST fails tests
def test_isa_defined_term_name():
    """
    Test an ISA RO-Crate where a defined term has no name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?defined_term schema:name ?name .
        }
        WHERE {
            ?defined_term a schema:DefinedTerm .
            ?defined_term schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "DefinedTerm entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_defined_term_name_of_incorrect_type():
    """
    Test an ISA RO-Crate where a defined term name has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?defined_term schema:name ?name .
        }
        INSERT {
            ?defined_term schema:name 42 .
        }
        WHERE {
            ?defined_term a schema:DefinedTerm .
            ?defined_term schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "DefinedTerm entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_defined_term_termCode():
    """
    Test an ISA RO-Crate where a defined term has no termCode.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?defined_term schema:termCode ?termCode .
        }
        WHERE {
            ?defined_term a schema:DefinedTerm .
            ?defined_term schema:termCode ?termCode .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "DefinedTerm entity SHOULD have at least one termCode"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_defined_term_termCode_of_incorrect_type():
    """
    Test an ISA RO-Crate where a defined term termCode has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?defined_term schema:termCode ?termCode .
        }
        INSERT {
            ?defined_term schema:termCode 42 .
        }
        WHERE {
            ?defined_term a schema:DefinedTerm .
            ?defined_term schema:termCode ?termCode .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["DefinedTerm termCode MUST be of type string"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
