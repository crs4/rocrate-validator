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
from tests.ro_crates import InvalidISARC, ValidROC
from tests.shared import do_entity_test, SPARQL_PREFIXES

# set up logging
logger = logging.getLogger(__name__)


# ----- MUST fails tests


def test_isa_additionaltype_not_investigation():
    """
    Test an ISA RO-Crate where no Dataset has `additionalType` of "Investigation".
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:additionalType "Investigation" .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Investigation" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Root Data Entity must be Investigation"],
        expected_triggered_issues=[
            "The root data entity must have additionalType of `Investigation`"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )

def test_isa_investigation_no_identifier():
    """
    Test an ISA RO-Crate where the investigation has no identifier.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().investigation_is_missing_identifier,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "The root data entity must have a non-empty identifier"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_investigation_identifier_not_string():
    """
    Test an ISA RO-Crate where the investigation has an identifier that is not a string.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().investigation_identifier_not_string,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "The root data entity must have a non-empty identifier"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_investigation_no_shoulds():
    """
    Test an ISA RO-Crate where the investigation is missing should properties.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().investigation_is_missing_shoulds,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "Investigation entity SHOULD have a dateCreated",
            "Investigation entity SHOULD have a creator"
        ],
        profile_identifier="isa-ro-crate"
    )

def test_isa_investigation_shoulds_have_wrong_types():
    """
    Test an ISA RO-Crate where the investigation's should properties have wrong types.
    """

    do_entity_test(
        rocrate_path=InvalidISARC().investigation_shoulds_have_wrong_types,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "Investigation dateCreated MUST be a valid date literal",
            "Investigation creator MUST be of type Person"
        ],
        profile_identifier="isa-ro-crate"
    )
