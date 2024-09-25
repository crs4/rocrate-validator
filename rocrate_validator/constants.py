# Copyright (c) 2024 CRS4
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

# Define allowed RDF extensions and serialization formats as map
import typing

from rdflib import Namespace

# Define SHACL namespace
SHACL_NS = "http://www.w3.org/ns/shacl#"

# Define the Validator namespace
VALIDATOR_NS = Namespace("https://github.com/crs4/rocrate-validator/")

# Define the Profiles Vocabulary namespace
PROF_NS = Namespace("http://www.w3.org/ns/dx/prof/")

# Define the Schema.org namespace
SCHEMA_ORG_NS = Namespace("http://schema.org/")

# Define RDF syntax namespace
RDF_SYNTAX_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

# Define the file name for the profile specification conforms to the Profiles Vocabulary
PROFILE_SPECIFICATION_FILE = "profile.ttl"

# Define the rocrate-metadata.json file name
ROCRATE_METADATA_FILE = "ro-crate-metadata.json"

# Define the default profiles name
DEFAULT_PROFILE_IDENTIFIER = "ro-crate-1.1"

# Define the default profiles path
DEFAULT_PROFILES_PATH = "profiles"

# Define the default README file name for the RO-Crate profile
DEFAULT_PROFILE_README_FILE = "README.md"

# Define the list of directories to ignore when loading profiles
IGNORED_PROFILE_DIRECTORIES = ["__pycache__", ".", "README.md", "LICENSE"]

# Define the list of enabled profile file extensions
PROFILE_FILE_EXTENSIONS = [".ttl", ".py"]

# Define the default ontology file name
DEFAULT_ONTOLOGY_FILE = "ontology.ttl"

# Define allowed RDF extensions and serialization formats as map
RDF_SERIALIZATION_FILE_FORMAT_MAP = {
    "xml": "xml",
    "pretty-xml": "pretty-xml",
    "trig": "trig",
    "n3": "n3",
    "turtle": "ttl",
    "nt": "nt",
    "json-ld": "json-ld"
}

# Define allowed RDF serialization formats
RDF_SERIALIZATION_FORMATS_TYPES = typing.Literal[
    "xml", "pretty-xml", "trig", "n3", "turtle", "nt", "json-ld"
]
RDF_SERIALIZATION_FORMATS = typing.get_args(RDF_SERIALIZATION_FORMATS_TYPES)

# Define allowed inference options
VALID_INFERENCE_OPTIONS_TYPES = typing.Literal["owlrl", "rdfs", "both", None]
VALID_INFERENCE_OPTIONS = typing.get_args(VALID_INFERENCE_OPTIONS_TYPES)

# Define allowed requirement levels
VALID_REQUIREMENT_LEVELS_TYPES = typing.Literal[
    'MAY', 'OPTIONAL', 'SHOULD', 'SHOULD_NOT',
    'REQUIRED', 'MUST', 'MUST_NOT', 'SHALL', 'SHALL_NOT', 'RECOMMENDED'
]
