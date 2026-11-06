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

"""Core API for graph transformers used by SHACL validation."""

from rocrate_validator.requirements.shacl.transformers.base import GraphTransformer
from rocrate_validator.requirements.shacl.transformers.pipeline import prepare_data_graph
from rocrate_validator.requirements.shacl.transformers.registry import graph_transformer
from rocrate_validator.requirements.shacl.transformers.vocabulary import (
    REQUIRES_GRAPH_TRANSFORMER_PREDICATE,
)

__all__ = [
    "REQUIRES_GRAPH_TRANSFORMER_PREDICATE",
    "GraphTransformer",
    "graph_transformer",
    "prepare_data_graph",
]
