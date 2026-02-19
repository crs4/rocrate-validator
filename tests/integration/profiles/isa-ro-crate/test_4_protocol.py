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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Protocol SHOULD have intended use"],
        expected_triggered_issues=["Protocol intended use MUST be of type string or DefinedTerm"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
