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


# ---- SHOULD fails tests


def test_5src_no_signoff_phase():
    """
    Test a Five Safes Crate where no Sign-Off phase is listed.
    """

    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> ?p ?o .
        }
        WHERE {
            <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> ?p ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhase"],
        expected_triggered_issues=[
            "There SHOULD be a Sign-Off Phase in the Final RO-Crate"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_no_name():
    """
    Test a Five Safes Crate where the Sign-Off phase has no name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:name ?name .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOff"],
        expected_triggered_issues=[
            "Sign Off phase MUST have a human-readable name string."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_wrong_type():
    """
    Test a Five Safes Crate where the Sign-Off phase has no name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff rdf:type ?type .
        }
        INSERT {
            ?signoff rdf:type <wrongtype> .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               rdf:type ?type .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOff"],
        expected_triggered_issues=["Sign Off phase MUST be a `schema:AssessAction`."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_wrong_action_status():
    """
    Test a Five Safes Crate where the Sign-Off phase has the wrong action status.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:actionStatus ?status .
        }
        INSERT {
            ?signoff schema:actionStatus <wrongstatus> .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:actionStatus ?status .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffStatus"],
        expected_triggered_issues=[
            "The value of actionStatus MUST be one of the allowed values:"
            + " PotentialActionStatus; ActiveActionStatus; CompletedActionStatus; FailedActionStatus."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_not_mentioned():
    """
    Test a Five Safes Crate where the Sign-Off phase is not mentioned by the MainRootEntity.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:mentions <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> .
        }
        WHERE {
            <./> schema:mentions <#signoff-3b741265-cfef-49ea-8138-a2fa149bf2f0> .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhase"],
        expected_triggered_issues=[
            "The Root Data Entity SHOULD mention a Sign-Off Phase Object"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_no_endtime():
    """
    Test a Five Safes Crate where the Sign-Off phase has no endTime.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:endTime ?endTime .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:endTime ?endTime .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseEndTime"],
        expected_triggered_issues=[
            "Sign Off object SHOULD have endTime property if action completed or failed."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_malformed_endtime():
    """
    Test a Five Safes Crate where the Sign-Off phase has an endTime
    in the wrong format.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:endTime ?endTime .
        }
        INSERT {
            ?signoff schema:endTime <2025-10-20> .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:endTime ?endTime .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["Timestamp Format"],
        expected_triggered_issues=[
            (
                "All `startTime` and `endTime` values MUST follow the RFC 3339 standard "
                "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_no_starttime():
    """
    Test a Five Safes Crate where the Sign-Off phase has no startTime.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:startTime ?startTime .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:startTime ?startTime .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseStartTime"],
        expected_triggered_issues=[
            "Sign Off object MAY have a startTime property if action is active, completed or failed."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_malformed_starttime():
    """
    Test a Five Safes Crate where the Sign-Off phase has a startTime
    in the wrong format.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:startTime ?startTime .
        }
        INSERT {
            ?signoff schema:startTime <2025-10-20> .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:startTime ?startTime .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["Timestamp Format"],
        expected_triggered_issues=[
            (
                "All `startTime` and `endTime` values MUST follow the RFC 3339 standard "
                "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_no_actionstatus():
    """
    Test a Five Safes Crate where the Sign-Off phase has no actionStatus.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:actionStatus ?actionStatus .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:actionStatus ?actionStatus .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=["The Sign-Off Phase SHOULD have an actionStatus"],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_no_agent():
    """
    Test a Five Safes Crate where the Sign-Off phase has no agent.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:agent ?agent .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:agent ?agent .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=["The Sign-Off Phase SHOULD have an agent"],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_no_instrument():
    """
    Test a Five Safes Crate where the Sign-Off phase has no TRE policy (instrument).
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:instrument ?instrument .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:instrument ?instrument .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=[
            "The Sign-Off Phase SHOULD have an TRE policy (instrument) with type CreativeWork"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_instrument_not_iri():
    """
    Test a Five Safes Crate where the Sign-Off phase TRE policy (instrument) is not an IRI.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:instrument ?instrument .
        }
        INSERT {
            ?signoff schema:instrument "Not a cross-reference" .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:instrument ?instrument .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=[
            "The Sign-Off Phase SHOULD have an TRE policy (instrument) with type CreativeWork"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_instrument_no_type():
    """
    Test a Five Safes Crate where the Sign-Off phase instrument has no type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?instrument rdf:type ?type .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:instrument ?instrument .
            ?instrument rdf:type ?type .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=[
            "The Sign-Off Phase SHOULD have an TRE policy (instrument) with type CreativeWork"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_instrument_no_name():
    """
    Test a Five Safes Crate where the Sign-Off phase instrument has no type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?instrument schema:name ?name .
        }
        WHERE {
           ?signoff a schema:AssessAction ;
               schema:additionalType <https://w3id.org/shp#SignOff> ;
               schema:instrument ?instrument .
            ?instrument schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=[
            "The Sign-Off Phase SHOULD have an TRE policy (instrument) with a human-readable name"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_object_notworkflow():
    """
    Test a Five Safes Crate where there is no workflow in the Sign-Off objects.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:object <https://workflowhub.eu/workflows/289?version=1> .
        }
        INSERT {
            ?signoff schema:object <notaworkflow> .
        }
        WHERE {
            ?signoff a schema:AssessAction ;
                schema:additionalType <https://w3id.org/shp#SignOff> ;
                schema:object <https://workflowhub.eu/workflows/289?version=1> .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=[
            "The Sign-Off Phase SHOULD list the workflow (mainEntity) as an object"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_signoff_phase_object_not_responsible_project():
    """
    Test a Five Safes Crate where there is no Responsible Project in the Sign-Off objects.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?signoff schema:object <#project-be6ffb55-4f5a-4c14-b60e-47e0951090c70> .
        }
        INSERT {
            ?signoff schema:object <notaresponsibleproject> .
        }
        WHERE {
            ?signoff a schema:AssessAction ;
                schema:additionalType <https://w3id.org/shp#SignOff> ;
                schema:object <#project-be6ffb55-4f5a-4c14-b60e-47e0951090c70> .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["SignOffPhaseProperties"],
        expected_triggered_issues=[
            "The Sign-Off Phase SHOULD list the Responsible Project (sourceOrganization) as an object"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
