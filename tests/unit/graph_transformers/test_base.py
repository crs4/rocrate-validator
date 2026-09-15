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

from abc import abstractmethod

import pytest
from rdflib import Graph, Literal, Namespace

from rocrate_validator.graph_transformers import GraphTransformer, graph_transformer
from rocrate_validator.graph_transformers import base as transformer_base
from rocrate_validator.graph_transformers.base import (
    get_registered_transformers,
    run_registered_transformers,
)

EXAMPLE = Namespace("https://example.org/")


def test_abstract_transformers_are_not_registered(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(transformer_base, "_TRANSFORMERS", {})

    class AbstractTransformer(GraphTransformer):
        @abstractmethod
        def transform(self, data_graph: Graph) -> Graph:
            raise NotImplementedError

    assert get_registered_transformers() == ()


def test_registered_transformers_run_in_order(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(transformer_base, "_TRANSFORMERS", {})
    trace = EXAMPLE.trace
    step = EXAMPLE.step

    @graph_transformer(order=20)
    def function_transformer(data_graph: Graph) -> Graph:
        assert (trace, step, Literal("class")) in data_graph
        data_graph.add((trace, step, Literal("function")))
        return data_graph

    class ClassTransformer(GraphTransformer):
        order = 10

        def transform(self, data_graph: Graph) -> Graph:
            data_graph.add((trace, step, Literal("class")))
            return data_graph

    source = Graph()
    transformed = run_registered_transformers(source)

    assert (trace, step, Literal("class")) in transformed
    assert (trace, step, Literal("function")) in transformed
    assert [item.order for item in get_registered_transformers()] == [10, 20]


def test_transformer_must_return_an_rdflib_graph(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(transformer_base, "_TRANSFORMERS", {})

    @graph_transformer()
    def invalid_transformer(data_graph: Graph) -> Graph:
        del data_graph
        return "not a graph"  # type: ignore[return-value]

    with pytest.raises(TypeError, match="did not return an RDFLib Graph"):
        run_registered_transformers(Graph())
