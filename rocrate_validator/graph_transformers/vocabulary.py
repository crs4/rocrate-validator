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

# Private vocabulary for annotations that exist only in the transient graph
# passed to pySHACL. These predicates describe validator bookkeeping, not
# RO-Crate metadata, and must never be serialized back into the crate.
MARKER_NS = Namespace("https://github.com/crs4/rocrate-validator/graph-transformers/")
VALIDATION_CANDIDATE_PREDICATE: URIRef = URIRef(MARKER_NS.validationCandidate)
