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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["DefinedTerm termCode MUST be of type string"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
