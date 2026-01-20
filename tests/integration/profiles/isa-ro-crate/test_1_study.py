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
import pytest
# set up logging
logger = logging.getLogger(__name__)


# ----- MUST fails tests

# WIP fix this test and replace the test below which makes use of an pre-made invalid RO-Crate 
# @pytest.mark.xfail(
#     reason="'Study MUST have base properties' check fails: The SPARQL modification does not remove all identifiers from Study entities"
# )
# def test_isa_study_no_identifier():
#     """
#     Test an ISA RO-Crate where a Study does not have an identifier.
#     """
#     sparql = (
#         SPARQL_PREFIXES
#         + """
#         PREFIX isa-ro-crate: <https://github.com/crs4/rocrate-validator/profiles/isa-ro-crate/>
#         DELETE {
#             ?study schema:identifier ?value .
#         }
#         WHERE {
#             ?study a schema:Dataset .
#             ?study schema:additionalType "Study" .
#         }
#         """
#     )

#     do_entity_test(
#         rocrate_path=ValidROC().isa_ro_crate,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["Study MUST have base properties"],
#         expected_triggered_issues=[
#             "Study entity MUST have a non-empty identifier of type string"
#         ],
#         profile_identifier="isa-ro-crate",
#         rocrate_entity_mod_sparql=sparql,
#     )

# WIP update these tests to actually do what the name/description say
def test_isa_study_no_identifier():
    """
    Test an ISA RO-Crate where a Study has no identifier.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().study_is_missing_identifier,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity MUST have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_study_identifier_not_string():
    """
    Test an ISA RO-Crate where a Study has an identifier that is not a string.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().study_identifier_not_string,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity MUST have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_study_name_not_string():
    """
    Test an ISA RO-Crate where a Study has a name that is not a string.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().study_name_not_string,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_study_correctly_referenced_from_investigation():
    """
    Test an ISA RO-Crate where a Study is referenced from the Investigation/Root Data Entity with wrong property.
    """
    do_entity_test(
        rocrate_path=InvalidISARC().study_is_linked_through_illegal_property,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Study MUST be directly referenced from Investigation (Root Data Entity)"],
        expected_triggered_issues=[
            "Study MUST be directly referenced in hasPart on the Investigation (Root Data Entity)"
        ],
        profile_identifier="isa-ro-crate",
    )

def test_isa_study_directly_referenced_from_investigation():
    """
    Test an ISA RO-Crate where a Study is not directly referenced from the Investigation/Root Data Entity.
    """
    do_entity_test(
        rocrate_path=InvalidISARC().study_is_not_directly_part_of_investigation,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Study MUST be directly referenced from Investigation (Root Data Entity)"],
        expected_triggered_issues=[
            "Study MUST be directly referenced in hasPart on the Investigation (Root Data Entity)"
        ],
        profile_identifier="isa-ro-crate",
    )

def test_isa_study_no_shoulds():
    """
    Test an ISA RO-Crate where the study is missing should properties.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().study_is_missing_shoulds,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity SHOULD have a dateCreated",
            "Study entity SHOULD have a datePublished",
            "Study entity SHOULD have a creator",
            "Study entity SHOULD have hasPart",
            "Study entity SHOULD have about",
            "Study entity SHOULD have a non-empty description of type string"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_study_shoulds_have_wrong_types():
    """
    Test an ISA RO-Crate where the study has should properties with wrong types.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().study_shoulds_have_wrong_types,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study dateCreated MUST be a valid date literal",
            "Study datePublished MUST be a valid date literal",
            "Study creator MUST be of type Person",
            "Study hasPart MUST be of type Dataset or File",
            "Study about MUST be of type LabProcess",
            "Study description MUST be of type string"
        ],
        profile_identifier="isa-ro-crate"
    )

# def test_isa_study_identifier():
#     """
#     Test an ISA RO-Crate where a Study does not have an identifier.
#     """
#     do_entity_test(
#         rocrate_path=InvalidISARC().study_is_missing_identifier,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["Study MUST have base properties"],
#         expected_triggered_issues=[
#             "Study entity MUST have a non-empty identifier of type string"
#         ],
#         profile_identifier="isa-ro-crate",
#     )
    
# def test_isa_study_name():
#     """
#     Test an ISA RO-Crate where a Study does not have a name.
#     """
#     do_entity_test(
#         rocrate_path=InvalidISARC().study_is_missing_name,
#         requirement_severity=Severity.REQUIRED,
#         expected_validation_result=False,
#         expected_triggered_requirements=["Study MUST have base properties"],
#         expected_triggered_issues=[
#             "Study entity MUST have a non-empty name of type string"
#         ],
#         profile_identifier="isa-ro-crate",
#     )