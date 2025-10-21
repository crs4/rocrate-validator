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


def funding_project_no_name(graph):
    SCHEMA = rdflib.Namespace("http://schema.org/")
    target_subject = rdflib.URIRef("#project-be6ffb55-4f5a-4c14-b60e-47e0951090c70")
    target_predicate = SCHEMA.name
    target_object = None

    for s, p, o in graph.triples((target_subject, target_predicate, target_object)):
        print(f"Removing: {s}, {p}, {o}")

    graph.remove((target_subject, target_predicate, target_object))

    return graph


def test_5src_funding_project_no_name():
    """\
    Test a Five Safes Crate where the funding Project does not have a name.
    """
    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Funding body Project"],
        expected_triggered_issues=[
            "The Project Entity MUST have a `name` property (as specified by schema.org)"
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_function=funding_project_no_name,
    )
