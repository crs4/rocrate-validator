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


def test_5src_root_data_entity_two_main_entities():
    """
    Add a 2nd RootDataEntity's mainEntity so maxCount=1 is violated.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        INSERT {
            # add an IRI that is NOT typed as schema:Dataset (e.g. a schema:SoftwareSourceCode)
            <./> schema:mainEntity <https://workflowhub.eu/workflows/289?version=2> .
            <https://workflowhub.eu/workflows/289?version=2> a schema:Dataset .
        }
        WHERE {
            <./> schema:mainEntity ?m .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "The RootDataEntity MUST have exactly one mainEntity property that is an IRI."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_root_data_entity_no_main_entity():
    """
    Remove the RootDataEntity's mainEntity so minCount=1 is violated.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:mainEntity ?m .
        }
        WHERE {
            <./> schema:mainEntity ?m .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "The RootDataEntity MUST have exactly one mainEntity property that is an IRI."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_root_data_entity_main_entity_not_dataset_iri():
    """
    Test a Five Safes Crate where the RootDataEntity's mainEntity is an IRI but not typed as schema:Dataset.
    (We point mainEntity to a new crate-local entity typed as something else.)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:mainEntity ?m .
        }
        INSERT {
            # add an IRI that is NOT typed as schema:Dataset (e.g. a schema:SoftwareSourceCode)
            <./> schema:mainEntity <./not-a-dataset> .
            <./not-a-dataset> a schema:SoftwareSourceCode .
        }
        WHERE {
            <./> schema:mainEntity ?m .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "The mainEntity pointed to by the RootDataEntity MUST be of type Dataset"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_main_entity_conformsTo_absent():
    """
    Test a Five Safes Crate where the mainEntity does not have the purl:conformsTo property
    (we remove from the graph the triplet 'mainEntity conformsTo ?o').
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX purl: <http://purl.org/dc/terms/>
        DELETE {
            ?dataset purl:conformsTo ?o .
        }
        WHERE {
            <./> schema:mainEntity ?dataset .
            ?dataset purl:conformsTo ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["mainEntity"],
        expected_triggered_issues=[
            "mainEntity MUST have one and only one `conformsTo` property."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_main_entity_has_two_conformsto():
    """
    Test a Five Safes Crate where the mainEntity -> purl:conformsTo has two
    objects.
    (we add second object to mainEntity -> purl:conformsTo to violate maxCount 1).
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX purl: <http://purl.org/dc/terms/>
        INSERT {
            ?main purl:conformsTo <https://w3id.org/workflowhub/workflow-ro-crate/2.0> .
        }
        WHERE {
            <./> schema:mainEntity ?main .
            ?main purl:conformsTo ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["mainEntity"],
        expected_triggered_issues=[
            "mainEntity MUST have one and only one `conformsTo` property."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_main_entity_conformsTo_invalid():
    """
    Test a Five Safes Crate where the mainEntity's conformsTo IRI does NOT start with
    "https://w3id.org/workflowhub/workflow-ro-crate" (violates the SHACL SPARQL constraint).
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        PREFIX purl: <http://purl.org/dc/terms/>
        DELETE {
            ?dataset purl:conformsTo ?iri .
        }
        INSERT {
            ?dataset purl:conformsTo <http://example.org/not-workflow-ro-crate> .
        }
        WHERE {
            <./> schema:mainEntity ?dataset .
            ?dataset purl:conformsTo ?iri .
            FILTER(STRSTARTS(STR(?iri), "https://w3id.org/workflowhub/workflow-ro-crate"))
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["mainEntity"],
        expected_triggered_issues=[
            "conformsTo IRI must start with https://w3id.org/workflowhub/workflow-ro-crate"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests


def test_5src_main_entity_missing_distribution_warning():
    """
    Test a Five Safes Crate where a mainEntity has an HTTP(S) IRI but no distribution with an HTTP(S) URL.
    This should trigger the SHACL warning about missing or non-HTTP(S) distributions.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:distribution ?dist .
        }
        WHERE {
            <./> schema:mainEntity ?dataset .
            ?dataset schema:distribution ?dist .
            FILTER (STRSTARTS(STR(?dataset), "http://") || STRSTARTS(STR(?dataset), "https://")) .
            FILTER (STRSTARTS(STR(?dist), "http://") || STRSTARTS(STR(?dist), "https://")) .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["mainEntity"],
        expected_triggered_issues=[
            "If mainEntity has an HTTP(S) @id SHOULD have at least one distribution with an HTTP(S) URL."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
