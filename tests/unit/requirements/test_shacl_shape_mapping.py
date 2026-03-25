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

from rdflib import BNode, Graph, Literal, Namespace, RDF

from rocrate_validator.constants import SHACL_NS
from rocrate_validator.requirements.shacl.utils import compute_key


def test_compute_key_distinguishes_contextual_bnodes():
    sh = Namespace(SHACL_NS)
    graph = Graph()

    shape_a = Namespace("https://example.org/")["ShapeA"]
    shape_b = Namespace("https://example.org/")["ShapeB"]
    prop_a = BNode()
    prop_b = BNode()
    path = Namespace("http://schema.org/")["error"]

    graph.add((shape_a, RDF.type, sh.NodeShape))
    graph.add((shape_a, sh.property, prop_a))
    graph.add((prop_a, RDF.type, sh.PropertyShape))
    graph.add((prop_a, sh.path, path))
    graph.add((prop_a, sh.minCount, Literal(1)))

    graph.add((shape_b, RDF.type, sh.NodeShape))
    graph.add((shape_b, sh.property, prop_b))
    graph.add((prop_b, RDF.type, sh.PropertyShape))
    graph.add((prop_b, sh.path, path))
    graph.add((prop_b, sh.minCount, Literal(1)))

    key_a = compute_key(graph, prop_a)
    key_b = compute_key(graph, prop_b)

    assert key_a != key_b
