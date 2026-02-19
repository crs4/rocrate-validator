# Copyright (c) 2026 DataPLANT, The University of Manchester
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
def test_isa_process_name():
    """
    Test an ISA RO-Crate where a Process does not have a name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?process schema:name ?name .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process MUST have name"],
        expected_triggered_issues=[
            "Process entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_not_correctly_referenced_from_dataset():
    """
    Test an ISA RO-Crate where a Process is referenced from a Dataset with wrong property.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?dataset schema:about ?process .
        }
        INSERT {
            ?dataset schema:mentions ?process .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:about ?process.
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=[
            "Process MUST be directly referenced from a dataset"
        ],
        expected_triggered_issues=[
            "Process MUST be directly referenced in about on a Dataset"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_no_object():
    """
    Test an ISA RO-Crate where a Process does not have an object.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?process schema:object ?object .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process schema:object ?object .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have an object"],
        expected_triggered_issues=["Process entity SHOULD have an object"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_object_incorrect_type():
    """
    Test an ISA RO-Crate where a Process has an object with the wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?process schema:object ?object .
        }
        INSERT {
            ?process schema:object 42 .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process schema:object ?object .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have an object"],
        expected_triggered_issues=[
            "Process objects MUST be of type File, Sample or BioSample"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_no_result():
    """
    Test an ISA RO-Crate where a Process does not have a result.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?process schema:result ?result .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process schema:result ?result .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have a result"],
        expected_triggered_issues=["Process entity SHOULD have a result"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_result_incorrect_type():
    """
    Test an ISA RO-Crate where a Process has a result with the wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        DELETE {
            ?process schema:result ?result .
        }
        INSERT {
            ?process schema:result 42 .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process schema:result ?result .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have a result"],
        expected_triggered_issues=[
            "Process results MUST be of type File, Sample or BioSample"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_no_value():
    """
    Test an ISA RO-Crate where a Process does not have a parameter value.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?process bioschemas-prop:parameterValue ?pv .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process bioschemas-prop:parameterValue ?pv .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have a parameter value"],
        expected_triggered_issues=["Process entity SHOULD have a parameter value"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_value_incorrect_type():
    """
    Test an ISA RO-Crate where a Process has a parameter value with the wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?process bioschemas-prop:parameterValue ?pv .
        }
        INSERT {
            ?process bioschemas-prop:parameterValue 42 .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process bioschemas-prop:parameterValue ?pv .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have a parameter value"],
        expected_triggered_issues=[
            "Process parameter values MUST be of type PropertyValue"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_no_protocol():
    """
    Test an ISA RO-Crate where a Process does not have a protocol.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?process bioschemas-prop:executesLabProtocol ?prot .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process bioschemas-prop:executesLabProtocol ?prot .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have a protocol"],
        expected_triggered_issues=["Process entity SHOULD have a protocol"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_process_protocol_incorrect_type():
    """
    Test an ISA RO-Crate where a Process has a protocol with the wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX bioschemas: <https://bioschemas.org/>
        PREFIX bioschemas-prop: <https://bioschemas.org/properties/>
        DELETE {
            ?process bioschemas-prop:executesLabProtocol ?prot .
        }
        INSERT {
            ?process bioschemas-prop:executesLabProtocol 42 .
        }
        WHERE {
            ?process a bioschemas:LabProcess .
            ?process bioschemas-prop:executesLabProtocol ?prot .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Process SHOULD have a protocol"],
        expected_triggered_issues=["Process protocols MUST be of type LabProtocol"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
