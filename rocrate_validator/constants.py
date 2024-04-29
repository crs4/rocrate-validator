# Define allowed RDF extensions and serialization formats as map
import typing

# Define SHACL namespace
SHACL_NS = "http://www.w3.org/ns/shacl#"

# Define RDF syntax namespace
RDF_SYNTAX_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

# Define the rocrate-metadata.json file name
ROCRATE_METADATA_FILE = "ro-crate-metadata.json"

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
