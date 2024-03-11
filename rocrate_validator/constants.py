# Define allowed RDF extensions and serialization formats as map
import typing

# Define SHACL namespace
SHACL_NS = "http://www.w3.org/ns/shacl#"
# Define the rocrate-metadata.json file name
ROCRATE_METADATA_FILE = "ro-crate-metadata.json"


# Define the list of directories to ignore when loading profiles
IGNORED_PROFILE_DIRECTORIES = ["__pycache__", ".", "README.md", "LICENSE"]

# Define the list of enabled profile file extensions
PROFILE_FILE_EXTENSIONS = [".ttl", ".py"]

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
VALID_INFERENCE_OPTIONS_TYPES = typing.Literal["owl", "rdfs", "both", None]
VALID_INFERENCE_OPTIONS = typing.get_args(VALID_INFERENCE_OPTIONS_TYPES)
