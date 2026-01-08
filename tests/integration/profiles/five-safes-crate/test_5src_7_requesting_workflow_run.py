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


def test_rocrate_does_not_have_createaction():
    """
    Test a Five Safes Crate where no `CreateAction` entity exists.
    (We remove the entire CreateAction entity from the RO-Crate)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action ?p ?o .
            ?s ?p2 ?action .
        }
        WHERE {
            ?action a schema:CreateAction .
            ?action ?p ?o .
            OPTIONAL { ?s ?p2 ?action . }
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "`RootDataEntity` MUST reference at least one `CreateAction` through `mentions`"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_rootdataentity_does_not_have_mentions_property():
    """
    Test a Five Safes Crate where RootDataEntity does not have the property mentions.
    (We remove the property mentions from the RootDataEntity entity)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:mentions ?o .
        }
        WHERE {
            <./> schema:mentions ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "`RootDataEntity` MUST reference at least one `CreateAction` through `mentions`"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_rootdataentity_does_not_mention_create_action():
    """
    Test a Five Safes Crate where `RootDataEntity` does not `mention` a `CreateAction` entity.
    (We replace the object of RooDataEntity --> mentions with a string literal).
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:mentions ?o .
        }
        INSERT {
            <./> schema:mentions "This is not a CreateAction entity" .
        }
        WHERE {
            <./> schema:mentions ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "`RootDataEntity` MUST reference at least one `CreateAction` through `mentions`"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_createaction_does_not_have_instrument_property():
    """
    Test a Five Safes Crate where `CreateAction` does not have the property `instrument`.
    (We remove the property `instrument` from the `CreateAction` entity)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action schema:instrument ?o .
        }
        WHERE {
           ?action schema:instrument ?o ;
                   a schema:CreateAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=[
            "`CreateAction` MUST have the `schema:instrument` property"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_createaction_does_not_reference_mainentity_via_instrument():
    """
    Test a Five Safes Crate where `CreateAction` --> `instrument` does not
    reference `mainEntity`.
    (We replace `mainEntity` with a literal as the object of `CreateAction` --> `instrument`)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action schema:instrument ?o .
        }
        INSERT {
            ?action schema:instrument "This is not the mainEntity" .
        }
        WHERE {
           ?action schema:instrument ?o ;
                   a schema:CreateAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=[
            "`CreateAction` --> `instrument` MUST reference the same entity as `Root Data Entity` --> `mainEntity`"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_createaction_object_does_not_reference_existing_entities():
    """
    Test a Five Safes Crate where `CreateAction` --> `object` does not
    reference an existing entity in the RO-Crate.
    (We replace the objects of `CreateAction` --> `object` with a literal.`)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action schema:object ?o .
        }
        INSERT {
            ?action schema:object "This is not an entity in the RO-Crate" .
        }
        WHERE {
           ?action schema:object ?o ;
                   a schema:CreateAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=[
            "Each `object` in `CreateAction` MUST reference an existing entity."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests


def test_createaction_does_not_have_object_property():
    """
    Test a Five Safes Crate where `CreateAction` does not have the property `object`.
    (We remove the property `object` from `CreateAction`)
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?action schema:object ?o .
        }
        WHERE {
           ?action schema:object ?o ;
                   a schema:CreateAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["CreateAction"],
        expected_triggered_issues=[
            "`CreateAction` SHOULD have the property `object` with IRI values."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
