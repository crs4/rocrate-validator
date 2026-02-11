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
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test, SPARQL_PREFIXES

# set up logging
logger = logging.getLogger(__name__)


# ----- MUST fails tests
def test_isa_article_headline():
    """
    Test an ISA RO-Crate where an article has no headline.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?article schema:headline ?headline .
        }
        WHERE {
            ?article a schema:ScholarlyArticle .
            ?article schema:headline ?headline .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Article entity MUST have a non-empty headline of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_article_headline_of_incorrect_type():
    """
    Test an ISA RO-Crate where an article headline has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?article schema:headline ?headline .
        }
        INSERT {
            ?article schema:headline 42 .
        }
        WHERE {
            ?article a schema:ScholarlyArticle .
            ?article schema:headline ?headline .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Article entity MUST have a non-empty headline of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_article_identifier():
    """
    Test an ISA RO-Crate where an article has no identifier.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?article schema:identifier ?identifier .
        }
        WHERE {
            ?article a schema:ScholarlyArticle .
            ?article schema:identifier ?identifier .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Article entity MUST have a non-empty identifier of type string or PropertyValue"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_article_identifier_of_incorrect_type():
    """
    Test an ISA RO-Crate where an article identifier has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?article schema:identifier ?identifier .
        }
        INSERT {
            ?article schema:identifier 42 .
        }
        WHERE {
            ?article a schema:ScholarlyArticle .
            ?article schema:identifier ?identifier .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Article entity MUST have a non-empty identifier of type string or PropertyValue"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_article_author():
    """
    Test an ISA RO-Crate where an article has no author.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?article schema:author ?author .
        }
        WHERE {
            ?article a schema:ScholarlyArticle .
            ?article schema:author ?author .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Article entity SHOULD have at least one author"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_article_author_of_incorrect_type():
    """
    Test an ISA RO-Crate where an article author has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?article schema:author ?author .
        }
        INSERT {
            ?article schema:author 42 .
        }
        WHERE {
            ?article a schema:ScholarlyArticle .
            ?article schema:author ?author .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Article author MUST be of type Person"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
