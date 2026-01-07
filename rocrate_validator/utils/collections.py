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


class MapIndex:

    def __init__(self, name: str, unique: bool = False):
        self.name = name
        self.unique = unique


class MultiIndexMap:
    def __init__(self, key: str = "id", indexes: list[MapIndex] = None):
        self._key = key
        # initialize an empty dictionary to store the indexes
        self._indices: list[MapIndex] = {}
        if indexes:
            for index in indexes:
                self.add_index(index)
        # initialize an empty dictionary to store the data
        self._data = {}

    @property
    def key(self) -> str:
        return self._key

    @property
    def keys(self) -> list[str]:
        return list(self._data.keys())

    @property
    def indices(self) -> list[str]:
        return list(self._indices.keys())

    def add_index(self, index: MapIndex):
        self._indices[index.name] = {"__meta__": index}

    def remove_index(self, index_name: str):
        self._indices.pop(index_name)

    def get_index(self, index_name: str) -> MapIndex:
        return self._indices.get(index_name)["__meta__"]

    def add(self, key, obj, **indices):
        self._data[key] = obj
        for index_name, index_value in indices.items():
            index = self.get_index(index_name)
            assert isinstance(index, MapIndex), f"Index {index_name} does not exist"
            if index_name in self._indices:
                if index_value not in self._indices[index_name]:
                    self._indices[index_name][index_value] = set() if not index.unique else key
                if not index.unique:
                    self._indices[index_name][index_value].add(key)

    def remove(self, key):
        obj = self._data.pop(key)
        for index_name, index in self._indices.items():
            index_value = getattr(obj, index_name)
            if index_value in index:
                index[index_value].remove(key)

    def values(self):
        return self._data.values()

    def get_by_key(self, key):
        return self._data.get(key)

    def get_by_index(self, index_name, index_value):
        if index_name == self._key:
            return self._data.get(index_value)
        index = self.get_index(index_name)
        assert isinstance(index, MapIndex), f"Index {index_name} does not exist"
        if index.unique:
            key = self._indices.get(index_name, {}).get(index_value)
            return self._data.get(key)
        keys = self._indices.get(index_name, {}).get(index_value, set())
        return [self._data[key] for key in keys]
