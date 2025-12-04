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


# WIP update these tests to actually do what the name/description say
def test_isa_assay_no_identifier():
    """
    Test an ISA RO-Crate where a Assay has no identifier.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().assay_is_missing_identifier,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Assay MUST have base properties"],
        expected_triggered_issues=[
            "Assay entity MUST have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_assay_identifier_not_string():
    """
    Test an ISA RO-Crate where a Assay has an identifier that is not a string.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().assay_identifier_not_string,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Root Data Entity must be Investigation"],
        expected_triggered_issues=[
            "Assay entity MUST have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_assay_correctly_referenced_from_investigation():
    """
    Test an ISA RO-Crate where a Assay is referenced from the Investigation/Root Data Entity with wrong property.
    """
    do_entity_test(
        rocrate_path=InvalidISARC().assay_is_linked_through_illegal_property,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Assay MUST be directly referenced from Investigation (Root Data Entity)"],
        expected_triggered_issues=[
            "Assay MUST be directly referenced in hasPart on the Investigation (Root Data Entity)"
        ],
        profile_identifier="isa-ro-crate",
    )

def test_isa_assay_directly_referenced_from_investigation():
    """
    Test an ISA RO-Crate where a Assay is not directly referenced from the Investigation/Root Data Entity.
    """
    do_entity_test(
        rocrate_path=InvalidISARC().assay_is_not_directly_part_of_investigation,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Assay MUST be directly referenced from Investigation (Root Data Entity)"],
        expected_triggered_issues=[
            "Assay MUST be directly referenced in hasPart on the Investigation (Root Data Entity)"
        ],
        profile_identifier="isa-ro-crate",
    )