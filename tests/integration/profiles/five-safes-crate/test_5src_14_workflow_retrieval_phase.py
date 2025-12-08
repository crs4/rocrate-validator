# Copyright (c) 2024-2025 CRS4
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
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


# ----- MUST fails tests

# # TO BE CHECKED AGAIN
# def test_5src_check_value_not_of_type_assess_action():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?this rdf:type ?type .
#         }
#         INSERT {
#             ?this rdf:type <something_wrong> .
#         }
#         WHERE {
#             ?this a schema:AssessAction ;
#                   schema:additionalType shp:CheckValue ;
#                   rdf:type ?type .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["CheckValue MUST be a `schema:AssessAction`."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_name_not_a_string():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?this schema:name ?name .
#         }
#         INSERT {
#             ?this schema:name 123 .
#         }
#         WHERE {
#             ?this schema:additionalType shp:CheckValue .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["CheckValue MUST have a human readable name string of at least 20 characters."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_name_not_long_enough():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?this schema:name ?name .
#         }
#         INSERT {
#             ?this schema:name "Short" .
#         }
#         WHERE {
#             ?this schema:additionalType shp:CheckValue .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["CheckValue MUST have a human readable name string of at least 20 characters."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_start_time_not_iso_standard():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?c schema:startTime ?t .
#         }
#         INSERT {
#             ?c schema:startTime "1st of Jan 2021" .
#         }
#         WHERE {
#             ?c schema:additionalType shp:CheckValue ;
#              schema:startTime ?t .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["`CheckValue` --> `startTime` MUST follows the RFC 3339 standard."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_end_time_not_iso_standard():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?c schema:endTime ?t .
#         }
#         INSERT {
#             ?c schema:endTime "1st of Jan 2021" .
#         }
#         WHERE {
#             ?c schema:additionalType shp:CheckValue ;
#              schema:endTime ?t .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["`CheckValue` --> `endTime` MUST follows the RFC 3339 standard."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_has_action_status_with_not_allowed_value():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?s schema:actionStatus ?o .
#         }
#         INSERT {
#             ?s schema:actionStatus "Not a good action status" .
#         }
#         WHERE {
#             ?s schema:additionalType <https://w3id.org/shp#CheckValue> ;
#                schema:actionStatus ?o .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["`CheckValue` --> `actionStatus` MUST have one of the allowed values."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# # ----- SHOULD fails tests

# def test_5src_root_data_entity_does_not_mention_check_value_entity():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>

#         DELETE {
#             <./> schema:mentions ?o .
#         }
#         WHERE {
#             ?o schema:additionalType shp:CheckValue ;
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.RECOMMENDED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["RootDataEntity"],
#         expected_triggered_issues=["RootDataEntity SHOULD mention a check value object."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_object_does_not_point_to_root_data_entity():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>

#         DELETE {
#             ?s schema:object <./> .
#         }
#         INSERT {
#             ?s schema:object "not the RootDataEntity" .
#         }
#         WHERE {
#             ?s schema:additionalType shp:CheckValue ;
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.RECOMMENDED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["`CheckValue` --> `object` SHOULD point to the root of the RO-Crate"],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_instrument_does_not_point_to_entity_with_type_defined_term():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?s rdf:type schema:DefinedTerm .
#         }
#         INSERT {
#             ?s rdf:type schema:Persona .
#         }
#         WHERE {
#             ?cv schema:additionalType shp:CheckValue ;
#                 schema:instrument ?s .
#             ?s rdf:type schema:DefinedTerm .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.RECOMMENDED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=[
#             "`CheckValue` --> `instrument` SHOULD point to an entity typed `schema:DefinedTerm`"
#             ],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_does_not_have_end_time():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?c schema:endTime ?t .
#         }
#         WHERE {
#             ?c schema:additionalType shp:CheckValue ;
#              schema:endTime ?t .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.RECOMMENDED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["`CheckValue` SHOULD have the `endTime` property."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_does_not_have_action_status_property():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?s schema:actionStatus ?o .
#         }
#         WHERE {
#             ?s schema:additionalType shp:CheckValue ;
#                schema:actionStatus ?o .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.RECOMMENDED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["CheckValue SHOULD have actionStatus property."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# def test_5src_check_value_does_not_point_to_an_agent():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?s schema:agent ?o .
#         }
#         WHERE {
#             ?s schema:additionalType shp:CheckValue ;
#                schema:agent ?o .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.RECOMMENDED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["`CheckValue` --> `agent` SHOULD reference the agent who initiated the check"],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )


# # ----- MAY fails tests

# def test_5src_check_value_does_not_have_start_time():
#     sparql = """
#         PREFIX schema: <http://schema.org/>
#         PREFIX shp:    <https://w3id.org/shp#>
#         PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

#         DELETE {
#             ?c schema:startTime ?t .
#         }
#         WHERE {
#             ?c schema:additionalType shp:CheckValue ;
#              schema:startTime ?t .
#         }
#         """

#     do_entity_test(
#         rocrate_path=ValidROC().five_safes_crate_result,
#         requirement_severity=Severity.OPTIONAL,
#         expected_validation_result=False,
#         expected_triggered_requirements=["CheckValue"],
#         expected_triggered_issues=["`CheckValue` MAY have the `startTime` property."],
#         profile_identifier="five-safes-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )
