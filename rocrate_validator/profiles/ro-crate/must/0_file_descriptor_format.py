# Copyright (c) 2024-2025 CRS4
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

from typing import Any

import rocrate_validator.log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils import HttpRequester

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="File Descriptor existence")
class FileDescriptorExistence(PyFunctionCheck):
    """The file descriptor MUST be present in the RO-Crate and MUST not be empty."""

    @check(name="File Descriptor Existence")
    def test_existence(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor is present in the RO-Crate
        """
        if not context.ro_crate.has_descriptor():
            message = f'file descriptor "{context.rel_fd_path}" is not present'
            context.result.add_issue(message, self)
            return False
        return True

    @check(name="File Descriptor size check")
    def test_size(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor is not empty
        """
        if not context.ro_crate.has_descriptor():
            message = f'file descriptor {context.rel_fd_path} is empty'
            context.result.add_issue(message, self)
            return False
        if context.ro_crate.metadata.size == 0:
            context.result.add_issue(f'RO-Crate "{context.rel_fd_path}" file descriptor is empty', self)
            return False
        return True


@requirement(name="File Descriptor JSON format")
class FileDescriptorJsonFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON file
    """
    @check(name="File Descriptor JSON format")
    def check(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor is in the correct format"""
        try:
            logger.debug("Checking validity of JSON file at %s", context.ro_crate.metadata)
            context.ro_crate.metadata.as_dict()
            return True
        except Exception as e:
            context.result.add_issue(
                f'RO-Crate file descriptor "{context.rel_fd_path}" is not in the correct format', self)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return False


@requirement(name="File Descriptor JSON-LD format")
class FileDescriptorJsonLdFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON-LD file
    """

    def __check_remote_context__(self, context_uri: str) -> bool:
        # Try to retrieve the context
        try:
            raw_data = HttpRequester().get(context_uri, headers={"Accept": "application/ld+json"})
            if raw_data.status_code != 200:
                raise RuntimeError(f"Unable to retrieve the JSON-LD context '{context_uri}'", self)
            logger.debug(f"Retrieved context from {context_uri}")

            # Try to parse the JSON-LD and access the context
            jsonLD = raw_data.json()["@context"]
            assert isinstance(jsonLD, dict)
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False

    def __check_contexts__(self, context: ValidationContext, jsonld_context: object) -> bool:
        """ Get the keys of the context URI """
        is_valid = True
        # if the context is a string, check if it is a valid URI
        if isinstance(jsonld_context, str):
            if not self.__check_remote_context__(jsonld_context):
                context.result.add_issue(
                    f'Unable to retrieve the JSON-LD context "{jsonld_context}"', self)
                is_valid = False

        # if the context is a dictionary, get the keys of the dictionary
        if isinstance(jsonld_context, dict):
            logger.debug(f"Detected dictionary context: {jsonld_context}")

        # if the context is a list of contexts, get the keys of each context
        if isinstance(jsonld_context, list):
            for ctx in jsonld_context:
                if not self.__check_contexts__(context, ctx):
                    is_valid = False
        # return if the context is valid
        return is_valid

    @check(name="File Descriptor @context property validation")
    def check_context(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor contains
        the @context property and it is a valid JSON-LD context
        """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            if "@context" not in json_dict:
                context.result.add_issue(
                    f'RO-Crate file descriptor "{context.rel_fd_path}" '
                    "does not contain a context", self)
                return False

            # Check if the context is valid
            return self.__check_contexts__(context, json_dict["@context"])
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False

    @check(name="File Descriptor JSON-LD must be flattened")
    def check_flattened(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor is flattened """

        def is_entity_flat_recursive(entity: Any, is_first: bool = True) -> bool:
            """ Recursively check if the given data corresponds to a flattened JSON-LD object
            and returns False if it does not and is not a root element
            """
            if isinstance(entity, dict):
                if is_first:
                    for _, elem in entity.items():
                        if not is_entity_flat_recursive(elem, False):
                            return False
                # if this is not the root element, it must not contain more properties than @id
                else:
                    if "@id" not in entity or len(entity) > 1:
                        return False
            if isinstance(entity, list):
                for element in entity:
                    if not is_entity_flat_recursive(element, False):
                        return False
            return True

        try:
            json_dict = context.ro_crate.metadata.as_dict()
            for entity in json_dict["@graph"]:
                if not is_entity_flat_recursive(entity):
                    context.result.add_issue(
                        f'RO-Crate file descriptor "{context.rel_fd_path}" '
                        f'is not fully flattened at entity "{entity.get("@id", entity)}"', self)
                    return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False

    @check(name="Validation of the @id property of the file descriptor entities")
    def check_identifiers(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor entities have the @id property """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            for entity in json_dict["@graph"]:
                if "@id" not in entity:
                    context.result.add_issue(
                        f"Entity \"{entity.get('name', None) or entity}\" "
                        f"of RO-Crate \"{context.rel_fd_path}\" "
                        "file descriptor does not contain the @id attribute", self)
                    return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False

    @check(name="Validation of the @type property of the file descriptor entities")
    def check_types(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor entities have the @type property """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            for entity in json_dict["@graph"]:
                if "@type" not in entity:
                    context.result.add_issue(
                        f"Entity \"{entity.get('name', None) or entity}\" "
                        f"of RO-Crate \"{context.rel_fd_path}\" "
                        "file descriptor does not contain the @type attribute", self)
                    return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False

    def __get_context_keys__(self, context: object) -> set:
        """ Get the keys of the context URI """
        if isinstance(context, str):
            return self.__get_remote_context_keys__(context)

        # if the context is a dictionary, get the keys of the dictionary
        if isinstance(context, dict):
            return set(context.keys())

        # if the context is a list of contexts, get the keys of each context
        if isinstance(context, list):
            keys = set()
            for ctx in context:
                keys.update(self.__get_context_keys__(ctx))
            return keys

    def __get_remote_context_keys__(self, context_uri: str) -> set:
        """ Get the keys of the context URI """

        logger.debug(f"Retrieving context from {context_uri}...")
        # Try to retrieve the context
        raw_data = HttpRequester().get(context_uri, headers={"Accept": "application/ld+json"})
        if raw_data.status_code != 200:
            raise RuntimeError(f"Unable to retrieve the JSON-LD context '{context_uri}'")

        logger.debug(f"Retrieved context from {context_uri}")

        # Get the keys of the context
        jsonLD = raw_data.json()
        jsonLD_ctx = jsonLD["@context"]
        if not isinstance(jsonLD_ctx, dict):
            raise RuntimeError("The context is not a dictionary", self)
        return set(jsonLD_ctx.keys())

    def __check_entity_keys__(self, entity: dict,
                              context_keys: set,
                              unexpected_keys: dict[str, int] = None) -> dict[str, int]:
        """ Check if the entity is in the correct format """

        def add_unexpected_key(k: str, u_keys: dict) -> None:
            """ Add a key to the unexpected keys dictionary """
            u_keys[k] = u_keys.get(k, 0) + 1

        # Keys that should be skipped
        SKIP_KEYS = {"@id", "@type", "@context"}

        # Ensure unexpected_keys is initialized
        if unexpected_keys is None:
            unexpected_keys = {}

        # If the entity is a dictionary, check each key
        if isinstance(entity, dict):
            for k, v in entity.items():
                if k not in context_keys and k not in SKIP_KEYS:
                    logger.debug(f"Key {k} not in context keys")
                    add_unexpected_key(k, unexpected_keys)
                if isinstance(v, (dict, list)):
                    self.__check_entity_keys__(v, context_keys, unexpected_keys)

        # If the entity is a list, check each element
        elif isinstance(entity, list):
            for elem in entity:
                self.__check_entity_keys__(elem, context_keys, unexpected_keys)

        return unexpected_keys

    @check(name="Validation of the compaction format of the file descriptor")
    def check_compaction(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor is in the **compacted** JSON-LD format """
        try:
            logger.debug("Checking compaction format of JSON-LD file at %s", context.ro_crate.metadata)
            json_dict = context.ro_crate.metadata.as_dict()
            logger.debug(f"JSONLD keys:{json_dict.keys()}")

            jsonld_context = json_dict.get("@context", None)
            logger.debug(f"Context: {jsonld_context}")

            try:
                context_keys = self.__get_context_keys__(jsonld_context)
                logger.debug(f"{context_keys}")
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
                context.result.add_issue(str(e), self)
                return False

            unexpected_keys = self.__check_entity_keys__(json_dict.get("@graph"), context_keys)
            logger.debug(f"Unexpected keys: {unexpected_keys}")
            if len(unexpected_keys) > 0:
                for k, v in unexpected_keys.items():
                    logger.debug(f"Key {k} appears {v} times")
                    # Add the correct suffix to the message
                    suffix = "s" if v > 1 else ""
                    # Check if k is a term or a URI
                    if k.startswith("http"):
                        context.result.add_issue(
                            f'The The {v} occurrence{suffix} of the "{k}" URI cannot be used as a key{suffix} "'
                            'because the compacted format requires simple terms as keys '
                            '(see https://www.w3.org/TR/json-ld-api/#compaction for more details).', self)
                    else:
                        context.result.add_issue(
                            f'The {v} occurrence{suffix} of the JSON-LD key "{k}" '
                            f'{"is" if v ==1 else "are"} not allowed in the compacted format '
                            'because it is not present in the @context of the document', self)
                return False

            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            context.result.add_issue(
                f'Unexpected error: {e}', self)
        return False
