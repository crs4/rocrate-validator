# Copyright (c) 2024-2026 CRS4
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

"""Regression coverage for the RO-Crate compact property-name policy."""

# Empty dictionaries are part of the helper contract; None must not pass.
# pylint: disable=use-implicit-booleaness-not-comparison

import json
from copy import deepcopy
from unittest.mock import Mock

import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

from rocrate_validator.utils.http import OfflineCacheMissError
from rocrate_validator.utils.jsonld import find_unexpected_compaction_keys, resolve_compaction_context


@pytest.mark.parametrize(
    ("definition", "version", "accepted"),
    [
        ("https://example.org/", 1.0, True),
        ("https://example.org/ns", 1.0, True),
        ("https://example.org#", 1.0, True),
        ({"@id": "https://example.org/"}, 1.0, True),
        ("https://example.org/", 1.1, True),
        ({"@id": "https://example.org/", "@prefix": True}, 1.1, True),
        ({"@id": "https://example.org/", "@prefix": False}, 1.1, False),
        ({"@id": "https://example.org/"}, 1.1, False),
        ({"@id": "https://example.org/ns", "@prefix": True}, 1.1, True),
        ("https://example.org/name", 1.1, False),
        (None, 1.0, False),
        ({"@id": None}, 1.0, False),
        ("@id", 1.0, False),
        ("relative/", 1.0, False),
    ],
)
def test_prefix_eligibility(definition, version, accepted):
    context = {"@version": version, "ex": definition}
    unexpected = find_unexpected_compaction_keys({"@id": "./", "ex:property": "value"}, context)
    assert unexpected == ({} if accepted else {"ex:property": 1})


def test_context_order_nullification_and_remote_loader():
    loader = Mock(return_value={"ex": "https://example.org/", "name": "http://schema.org/name"})
    context = ["https://example.org/context", {"ex": None}]
    before = deepcopy(context)
    definitions = resolve_compaction_context(context, loader)
    assert find_unexpected_compaction_keys({"ex:property": 1, "name": "test"}, definitions) == {"ex:property": 1}
    loader.assert_called_once_with("https://example.org/context")
    assert context == before
    assert resolve_compaction_context([{"ex": "https://example.org/"}, None], loader) == {}


def test_remote_cycles_fail():
    loader = Mock(return_value="https://example.org/context")
    with pytest.raises(ValueError, match="Recursive JSON-LD context"):
        resolve_compaction_context("https://example.org/context", loader)


def test_remote_cache_miss_propagates():
    loader = Mock(side_effect=OfflineCacheMissError("https://example.org/context"))
    with pytest.raises(OfflineCacheMissError):
        resolve_compaction_context("https://example.org/context", loader)


def test_compact_namespace_definition():
    definitions = {"base": "https://example.org/", "ex": "base:terms#"}
    assert find_unexpected_compaction_keys({"ex:property": "value"}, definitions) == {}


def test_counts_and_non_node_payloads():
    entity = [
        {"@id": "./", "ex:property": [{"@value": "value", "@language": "en"}], "unknown": 1},
        {"@id": "#node", "unknown": 2, "@context": {"ex": "https://example.org/"}},
    ]
    assert find_unexpected_compaction_keys(entity, {"ex": "https://example.org/"}) == {"unknown": 2}


def test_explicit_terms_and_absolute_iri_policy():
    definitions = {"ex:property": "https://example.org/property", "ex": "https://example.org/"}
    assert find_unexpected_compaction_keys({"ex:property": 1}, definitions) == {}
    assert find_unexpected_compaction_keys({"https://example.org/property": 1}, definitions) == {
        "https://example.org/property": 1
    }


def test_prefix_and_explicit_term_preserve_rdf():
    prefixed = {"@context": {"ex": "https://example.org/"}, "@id": "https://example.org/node", "ex:property": "value"}
    explicit = {"@context": {"property": "https://example.org/property"}, "@id": prefixed["@id"], "property": "value"}
    assert isomorphic(
        Graph().parse(data=json.dumps(prefixed), format="json-ld"),
        Graph().parse(data=json.dumps(explicit), format="json-ld"),
    )


@pytest.mark.parametrize("disabled", [None, {"@id": None}])
def test_explicitly_disabled_compact_key_does_not_fall_back_to_prefix(disabled):
    definitions = {"ex": "https://example.org/", "ex:property": disabled}
    assert find_unexpected_compaction_keys({"ex:property": 1}, definitions) == {"ex:property": 1}


def test_remote_context_reset_clears_previous_definitions():
    loader = Mock(return_value=[None, {"new": "https://example.org/"}])
    definitions = resolve_compaction_context([{"old": "https://example.org/"}, "https://example.org/context"], loader)
    assert definitions == {"new": "https://example.org/"}


def test_later_namespace_override_does_not_rewrite_previous_mapping():
    definitions = resolve_compaction_context(
        [
            {"base": "https://example.org/", "ex": "base:terms#"},
            {"base": "https://other.example/"},
        ],
        Mock(),
    )
    assert definitions["ex"] == "https://example.org/terms#"
    assert definitions["base"] == "https://other.example/"


def test_remote_failure_is_not_ignored():
    loader = Mock(side_effect=RuntimeError("Unable to retrieve context"))
    with pytest.raises(RuntimeError, match="Unable to retrieve"):
        resolve_compaction_context("https://example.org/context", loader)


def test_relative_remote_reference_uses_parent_context_url():
    loader = Mock(side_effect=["nested.jsonld", {"ex": "https://example.org/"}])
    definitions = resolve_compaction_context("https://example.org/context/index.jsonld", loader)
    assert loader.call_args_list[-1].args == ("https://example.org/context/nested.jsonld",)
    assert find_unexpected_compaction_keys({"ex:property": 1}, definitions) == {}


@pytest.mark.parametrize(
    "definitions",
    [
        {"base": "https://example.org/", "ex": "base"},
        {"base": "https://example.org/", "ex": {"@id": "base"}},
    ],
)
def test_namespace_alias(definitions):
    assert find_unexpected_compaction_keys({"ex:property": 1}, definitions) == {}


def test_cyclic_namespace_alias_is_not_a_prefix():
    assert find_unexpected_compaction_keys({"ex:property": 1}, {"ex": "other", "other": "ex"}) == {"ex:property": 1}
