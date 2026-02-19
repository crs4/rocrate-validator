# Copyright (c) 2026 DataPLANT
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
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
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Article author MUST be of type Person"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
