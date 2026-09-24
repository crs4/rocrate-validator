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

from rdflib import Namespace, URIRef

# Shapes request bundled transformers explicitly through this predicate. This
# keeps private annotations and graph-copying overhead out of unrelated SHACL
# validations.
VALIDATOR_NS = Namespace("https://github.com/crs4/rocrate-validator/")
REQUIRES_GRAPH_TRANSFORMER_PREDICATE: URIRef = URIRef(VALIDATOR_NS.requiresGraphTransformer)

__all__ = ["REQUIRES_GRAPH_TRANSFORMER_PREDICATE"]
