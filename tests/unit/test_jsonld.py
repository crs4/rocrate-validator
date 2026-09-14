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

from rocrate_validator.utils.jsonld import find_singleton_property_arrays


def test_find_singleton_property_arrays_preserves_jsonld_semantics():
    metadata = {
        "@context": [
            {
                "setProperty": {"@id": "https://example.org/setProperty", "@container": "@set"},
                "listProperty": {"@id": "https://example.org/listProperty", "@container": "@list"},
            }
        ],
        "@graph": [
            {
                "@id": "./",
                "@type": ["Dataset", "Thing"],
                "singletonReference": [{"@id": "file.txt"}],
                "singletonLiteral": ["one"],
                "multipleValues": ["one", "two"],
                "emptyValues": [],
                "setProperty": ["one"],
                "listProperty": ["one"],
            },
            {"@id": "file.txt", "name": [{"@value": "File"}]},
        ],
    }

    assert find_singleton_property_arrays(metadata) == [
        ("./", "singletonReference"),
        ("./", "singletonLiteral"),
        ("file.txt", "name"),
    ]


def test_find_singleton_property_arrays_ignores_invalid_graph_shape():
    assert find_singleton_property_arrays({"@context": [], "@graph": {}}) == []
