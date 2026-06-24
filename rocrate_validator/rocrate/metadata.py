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

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from rdflib import Graph

from rocrate_validator.utils import log as logging

from .entity import ROCrateEntity

if TYPE_CHECKING:
    from .base import ROCrate

# set up logging
logger = logging.getLogger(__name__)


class ROCrateMetadata:
    METADATA_FILE_DESCRIPTOR = "ro-crate-metadata.json"

    def __init__(self, ro_crate: ROCrate, metadata_dict: dict | None = None) -> None:
        self._ro_crate = ro_crate
        self._dict = metadata_dict
        self._json: str | None = json.dumps(metadata_dict) if metadata_dict else None
        self._graph: Graph | None = None

    @property
    def ro_crate(self) -> ROCrate:
        return self._ro_crate

    @property
    def size(self) -> int:
        try:
            return len(self.as_json())
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error computing entity JSON size")
            return 0

    def get_file_descriptor_entity(self) -> ROCrateEntity:
        metadata_file_descriptor = self.get_entity(self.ro_crate.metadata_descriptor_id)
        if metadata_file_descriptor:
            return metadata_file_descriptor

        for entity in self.get_entities():
            if not entity.id or not entity.id.endswith(self.METADATA_FILE_DESCRIPTOR):
                continue
            if entity.has_type("CreativeWork"):
                return entity

        raise ValueError("no metadata file descriptor in crate")

    def get_root_data_entity(self) -> ROCrateEntity:
        metadata_file_descriptor = self.get_file_descriptor_entity()
        main_entity = metadata_file_descriptor.get_property("about")
        if not main_entity:
            raise ValueError("no main entity in metadata file descriptor")
        return main_entity

    def get_root_data_entity_conforms_to(self) -> list[str] | None:
        try:
            root_data_entity = self.get_root_data_entity()
            result = root_data_entity.get_property("conformsTo", [])
            if result is None:
                return None
            if not isinstance(result, list):
                result = [result]
            return [_.id for _ in result]
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error getting entity image")
            return None

    def get_main_workflow(self) -> ROCrateEntity:
        root_data_entity = self.get_root_data_entity()
        main_workflow = root_data_entity.get_property("mainEntity")
        if not main_workflow:
            raise ValueError("no main workflow in metadata file descriptor")
        return main_workflow

    def get_entity(self, entity_id: str) -> ROCrateEntity | None:
        for entity in self.as_dict().get("@graph", []):
            if entity.get("@id") == entity_id:
                return ROCrateEntity(self, entity)
        return None

    def get_entities(self) -> list[ROCrateEntity]:
        return [ROCrateEntity(self, entity) for entity in self.as_dict().get("@graph", [])]

    def get_entities_by_type(self, entity_type: str | list[str]) -> list[ROCrateEntity]:
        entity_types = [entity_type] if isinstance(entity_type, str) else entity_type
        return [e for e in self.get_entities() if e.has_types(entity_types)]

    def get_dataset_entities(self) -> list[ROCrateEntity]:
        return self.get_entities_by_type("Dataset")

    def get_file_entities(self) -> list[ROCrateEntity]:
        return self.get_entities_by_type("File")

    def get_data_entities(self, exclude_web_data_entities: bool = False) -> list[ROCrateEntity]:
        if not exclude_web_data_entities:
            return self.get_entities_by_type(["Dataset", "File"])
        return [e for e in self.get_entities_by_type(["Dataset", "File"]) if not e.is_remote()]

    def get_web_data_entities(self) -> list[ROCrateEntity]:
        return [
            entity
            for entity in self.get_entities()
            if (entity.has_type("File") or entity.has_type("Dataset")) and entity.is_remote()
        ]

    def get_conforms_to(self) -> list[str] | None:
        try:
            file_descriptor = self.get_file_descriptor_entity()
            result = file_descriptor.get_property("conformsTo", [])
            if result is None:
                return None
            if not isinstance(result, list):
                result = [result]
            return [_.id for _ in result]
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error getting entity identifiers by type")
            return None

    def as_json(self) -> str:
        if not self._json:
            self._json = cast(
                "str", self.ro_crate.get_file_content(Path(self.ro_crate.metadata_descriptor_id), binary_mode=False)
            )
        return self._json

    def as_dict(self) -> dict[Any, Any]:
        if not self._dict:
            # if the dictionary is not cached, load it
            self._dict = json.loads(self.as_json())
        assert self._dict is not None, "Metadata dictionary should not be None after loading"
        return self._dict

    def as_graph(self, publicID: str | None = None) -> Graph:
        if not self._graph:
            # if the graph is not cached, load it
            self._graph = Graph(base=publicID or str(self.ro_crate.uri))
            self._graph.parse(data=self.as_json(), format="json-ld")
        return self._graph

    def __str__(self) -> str:
        return f"Metadata({self.ro_crate})"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ROCrateMetadata):
            return False
        return self.ro_crate == other.ro_crate

    def __hash__(self) -> int:
        return hash(self.ro_crate)
