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

"""
Library of shared functions for testing RO-Crate profiles
"""

import json
import logging
import shutil
import tempfile
import rdflib
from collections.abc import Collection
from pathlib import Path
from typing import Optional, TypeVar, Union
from urllib.parse import urljoin

from rocrate_validator import models, services
from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER

logger = logging.getLogger(__name__)


T = TypeVar("T")

SPARQL_PREFIXES = """
PREFIX schema: <http://schema.org/>
PREFIX dct: <http://purl.org/dc/terms/>
"""


def first(c: Collection[T]) -> T:
    return next(iter(c))


def load_graph_and_preserve_relative_ids(json_data, base="http://example.org/"):

    rel_ids = set()

    def collect_ids(obj):
        if isinstance(obj, dict):
            if "@id" in obj:
                idv = obj["@id"]
                if isinstance(idv, str) and (idv.startswith("./") or idv.startswith("../") or idv.startswith("#")):
                    rel_ids.add(idv)
            for v in obj.values():
                collect_ids(v)
        elif isinstance(obj, list):
            for item in obj:
                collect_ids(item)

    collect_ids(json_data)

    g = rdflib.Graph()
    g.parse(data=json_data, format="json-ld", publicID=base)

    mapping = {}
    for rid in rel_ids:
        expanded = urljoin(base, rid)
        mapping[expanded] = rid

    def replace_uri_in_graph(graph, old_uri_str, new_uri_str):
        new = rdflib.URIRef(new_uri_str)
        triples_to_add = []
        triples_to_remove = []
        for s, p, o in graph.triples((None, None, None)):
            s2 = new if (isinstance(s, rdflib.URIRef) and str(s) == old_uri_str) else s
            o2 = new if (isinstance(o, rdflib.URIRef) and str(o) == old_uri_str) else o
            if (s2, p, o2) != (s, p, o):
                triples_to_remove.append((s, p, o))
                triples_to_add.append((s2, p, o2))
        for t in triples_to_remove:
            graph.remove(t)
        for t in triples_to_add:
            graph.add(t)

    for expanded, rel in mapping.items():
        replace_uri_in_graph(g, expanded, rel)

    return g


def do_entity_test(
        rocrate_path: Union[Path, str],
        requirement_severity: models.Severity,
        expected_validation_result: bool,
        expected_triggered_requirements: Optional[list[str]] = None,
        expected_triggered_issues: Optional[list[str]] = None,
        abort_on_first: bool = False,
        profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER,
        rocrate_entity_patch: Optional[dict] = None,
        rocrate_entity_mod_sparql: Optional[str] = None,
        skip_checks: Optional[list[str]] = (),
        **kwargs
):
    """
    Shared function to test a RO-Crate entity.

    Additional keyword arguments (kwargs) are passed through to ValidationSettings,
    allowing individual tests to tweak settings as needed.
    """
    assert not (rocrate_entity_patch and rocrate_entity_mod_sparql), \
        "Cannot use rocrate_entity_patch and rocrate_entity_mod_sparql together"

    # declare variables
    failed_requirements = None
    detected_issues = None

    if not isinstance(rocrate_path, Path):
        rocrate_path = Path(rocrate_path)

    temp_rocrate_path = None
    if any([rocrate_entity_patch, rocrate_entity_mod_sparql]) and rocrate_path.is_dir():
        # create a temporary copy of the RO-Crate
        temp_rocrate_path = Path(tempfile.TemporaryDirectory().name)
        # copy the RO-Crate to the temporary path using shutil
        shutil.copytree(rocrate_path, temp_rocrate_path)
        # load the RO-Crate metadata as RO-Crate JSON-LD
        with open(temp_rocrate_path / "ro-crate-metadata.json", "r") as f:
            rocrate = json.load(f)
        # update the RO-Crate metadata with the patch
        if rocrate_entity_patch is not None:
            for key, value in rocrate_entity_patch.items():
                for entity in rocrate["@graph"]:
                    if entity["@id"] == key:
                        entity.update(value)
                        break
            # save the updated RO-Crate metadata
            with open(temp_rocrate_path / "ro-crate-metadata.json", "w") as f:
                json.dump(rocrate, f)
        # update the RO-Crate metadata using SPARQL, if required
        if rocrate_entity_mod_sparql is not None:
            rocrate_graph = load_graph_and_preserve_relative_ids(rocrate)

            rocrate_graph.update(rocrate_entity_mod_sparql)

            # save the updated RO-Crate metadata
            context = "https://w3id.org/ro/crate/1.1/context"
            rocrate_graph.serialize(
                Path(temp_rocrate_path, "ro-crate-metadata.json"),
                format="json-ld",
                context=context,
                indent=2,
                use_native_types=True,
            )
        rocrate_path = temp_rocrate_path

    if expected_triggered_requirements is None:
        expected_triggered_requirements = []
    if expected_triggered_issues is None:
        expected_triggered_issues = []

    try:
        logger.debug("Testing RO-Crate @ path: %s", rocrate_path)
        logger.debug("Requirement severity: %s", requirement_severity)
        logger.debug("Checks to skip: %s", skip_checks)

        # set abort_on_first to False
        abort_on_first = abort_on_first

        # validate RO-Crate
        result: models.ValidationResult = \
            services.validate(models.ValidationSettings(**{
                "rocrate_uri": rocrate_path,
                "requirement_severity": requirement_severity,
                "abort_on_first": abort_on_first,
                "profile_identifier": profile_identifier,
                "skip_checks": skip_checks,
                **kwargs
            }))
        logger.debug("Expected validation result: %s", expected_validation_result)

        assert result.context is not None, "Validation context should not be None"
        f"Expected requirement severity to be {requirement_severity}, but got {result.context.requirement_severity}"
        assert result.passed() == expected_validation_result, \
            f"RO-Crate should be {'valid' if expected_validation_result else 'invalid'}"

        # check requirement
        failed_requirements = [_.name for _ in result.failed_requirements]
        # assert len(failed_requirements) == len(expected_triggered_requirements), \
        #     f"Expected {len(expected_triggered_requirements)} requirements to be "\
        #     f"triggered, but got {len(failed_requirements)}"

        # check that the expected requirements are triggered
        for expected_triggered_requirement in expected_triggered_requirements:
            if expected_triggered_requirement not in failed_requirements:
                assert False, f"The expected requirement " \
                    f"\"{expected_triggered_requirement}\" was not found in the failed requirements"

        # check requirement issues
        detected_issues = [issue.message for issue in result.get_issues(requirement_severity)
                           if issue.message is not None]
        logger.debug("Detected issues: %s", detected_issues)
        logger.debug("Expected issues: %s", expected_triggered_issues)
        for expected_issue in expected_triggered_issues:
            if not any(expected_issue in issue for issue in detected_issues):  # support partial match
                assert False, f"The expected issue \"{expected_issue}\" was not found in the detected issues"
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(e)
            logger.debug("Failed to validate RO-Crate @ path: %s", rocrate_path)
            logger.debug("Requirement severity: %s", requirement_severity)
            logger.debug("Expected validation result: %s", expected_validation_result)
            logger.debug("Expected triggered requirements: %s", expected_triggered_requirements)
            logger.debug("Expected triggered issues: %s", expected_triggered_issues)
            logger.debug("Failed requirements: %s", failed_requirements)
            logger.debug("Detected issues: %s", detected_issues)
        raise e
    finally:
        # cleanup
        if temp_rocrate_path is not None:
            logger.debug("Cleaning up temporary RO-Crate @ path: %s", temp_rocrate_path)
            shutil.rmtree(temp_rocrate_path)
