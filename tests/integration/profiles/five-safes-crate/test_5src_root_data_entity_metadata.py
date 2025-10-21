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
import rdflib

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_5src_root_data_entity_no_source_organization():
    """\
    Test a Five Safes Crate where the Root Data Entity it does not reference a sourceOrganization.
    """
    def remove_source_org(graph):
        SCHEMA = rdflib.Namespace("http://schema.org/")
        target_subject = rdflib.URIRef("./")
        target_predicate = SCHEMA.sourceOrganization
        target_object = None

        for s, p, o in graph.triples((target_subject, target_predicate, target_object)):
            print(f"Removing: {s}, {p}, {o}")

        graph.remove((target_subject, target_predicate, target_object))

        return graph

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Five Safes Crate Root Data Entity REQUIRED properties"],
        expected_triggered_issues=[
            """The Root Data Entity MUST have a `sourceOrganization` property  (as specified by schema.org).
                   SHOULD link to a Contextual Entity in the RO-Crate Metadata File with a name."""
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_function=remove_source_org,
    )


def test_5src_root_data_entity_source_organization_not_entity():
    """\
    Test a Five Safes Crate where the Root Data Entity it does not reference a sourceOrganization.
    """
    def replace_source_org(graph):
        SCHEMA = rdflib.Namespace("http://schema.org/")
        target_subject = rdflib.URIRef("./")
        target_predicate = SCHEMA.sourceOrganization
        original_object = None
        new_object = rdflib.Literal('Investigation of cancer (TRE72 project 81)')

        for s, p, o in graph.triples((target_subject, target_predicate, original_object)):
            print(f"Replacing: {s}, {p}, {o}")

        graph.remove((target_subject, target_predicate, original_object))
        graph.add((target_subject, target_predicate, new_object))

        return graph

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Five Safes Crate Root Data Entity REQUIRED properties"],
        expected_triggered_issues=[
            """The Root Data Entity MUST have a `sourceOrganization` property  (as specified by schema.org).
                   SHOULD link to a Contextual Entity in the RO-Crate Metadata File with a name."""
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_function=replace_source_org,
    )
