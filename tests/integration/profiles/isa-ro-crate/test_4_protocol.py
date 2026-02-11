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
def test_isa_protocol_no_name():
    """
    Test an ISA RO-Crate where a Protocol does not have a name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?protocol schema:name ?name .
        }
        WHERE {
            ?protocol a bioschemas:LabProtocol .
            ?protocol schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Protocol SHOULD have name"],
        expected_triggered_issues=[
            "Protocol entity SHOULD have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_protocol_name_incorrect_type():
    """
    Test an ISA RO-Crate where a Protocol has a name with the wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?protocol schema:name ?name .
        }
        INSERT {
            ?protocol schema:name 42 .
        }
        WHERE {
            ?protocol a bioschemas:LabProtocol .
            ?protocol schema:name ?name .
        }
        """
    )
    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Protocol SHOULD have name"],
        expected_triggered_issues=["Protocol name MUST be of type string"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_protocol_no_description():
    """
    Test an ISA RO-Crate where a Protocol does not have a description.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?protocol schema:description ?description .
        }
        WHERE {
            ?protocol a bioschemas:LabProtocol .
            ?protocol schema:description ?description .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Protocol SHOULD have description"],
        expected_triggered_issues=[
            "Protocol entity SHOULD have a non-empty description of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_protocol_description_incorrect_type():
    """
    Test an ISA RO-Crate where a Protocol has a description with the wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?protocol schema:description ?description .
        }
        INSERT {
            ?protocol schema:description 42 .
        }
        WHERE {
            ?protocol a bioschemas:LabProtocol .
            ?protocol schema:description ?description .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Protocol SHOULD have description"],
        expected_triggered_issues=["Protocol description MUST be of type string"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_protocol_no_intendedUse():
    """
    Test an ISA RO-Crate where a Protocol does not have an intended use.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?protocol bioschemas-prop:intendedUse ?intendedUse .
        }
        WHERE {
            ?protocol a bioschemas:LabProtocol .
            ?protocol bioschemas-prop:intendedUse ?intendedUse .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Protocol SHOULD have intended use"],
        expected_triggered_issues=["Protocol entity SHOULD have an intended use"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_protocol_intendedUse_incorrect_type():
    """
    Test an ISA RO-Crate where a Protocol has an intended use with the wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?protocol bioschemas-prop:intendedUse ?intendedUse .
        }
        INSERT {
            ?protocol bioschemas-prop:intendedUse 42 .
        }
        WHERE {
            ?protocol a bioschemas:LabProtocol .
            ?protocol bioschemas-prop:intendedUse ?intendedUse .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Protocol SHOULD have intended use"],
        expected_triggered_issues=["Protocol intended use MUST be of type DefinedTerm"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
