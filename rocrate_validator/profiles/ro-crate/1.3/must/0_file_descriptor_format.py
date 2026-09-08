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

import json
import re
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester

# set up logging
logger = logging.getLogger(__name__)

# Property keys whose string values are literals (e.g. names, dates, URLs) rather
# than references to other entities, so a matching @id must not be flagged.
_LITERAL_KEYS = frozenset(
    {
        "name",
        "description",
        "encodingFormat",
        "contentSize",
        "datePublished",
        "keywords",
        "creditText",
        "contentUrl",
        "copyrightNotice",
        "version",
        "softwareVersion",
        "value",
        "propertyID",
        "actionStatus",
        "error",
        "startTime",
        "endTime",
        "url",
        "identifier",
    }
)


@requirement(name="File Descriptor existence")
class FileDescriptorExistence(PyFunctionCheck):
    """The file descriptor MUST be present in the RO-Crate and MUST not be empty."""

    @check(name="File Descriptor Existence")
    def test_existence(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor is present in the RO-Crate
        """
        if context.settings.metadata_only:
            logger.debug("Skipping file descriptor existence check in metadata-only mode")
            return True
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
        if context.settings.metadata_only:
            logger.debug("Skipping file descriptor existence check in metadata-only mode")
            return True
        if not context.ro_crate.has_descriptor():
            message = f"file descriptor {context.rel_fd_path} is empty"
            context.result.add_issue(message, self)
            return False
        if context.ro_crate.metadata.size == 0:
            context.result.add_issue(f'RO-Crate "{context.rel_fd_path}" file descriptor is empty', self)
            return False
        return True


@requirement(name="File Descriptor UTF-8 encoding")
class FileDescriptorEncodingCheck(PyFunctionCheck):
    """
    The file descriptor MUST be UTF-8 encoded
    """

    @check(name="File Descriptor UTF-8 encoding")
    def check(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor is UTF-8 encoded
        """
        try:
            raw_data = context.ro_crate.get_file_content(
                Path(context.ro_crate.metadata_descriptor_id), binary_mode=True
            )
            if isinstance(raw_data, str):
                return True
            raw_data.decode("utf-8")
            return True
        except Exception:
            context.result.add_issue(f'RO-Crate file descriptor "{context.rel_fd_path}" is not UTF-8 encoded', self)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
            return False


@requirement(name="File Descriptor JSON format")
class FileDescriptorJsonFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON file
    """

    @check(name="File Descriptor JSON format")
    def check(self, context: ValidationContext) -> bool:
        """Check if the file descriptor is in the correct format"""
        try:
            logger.debug("Checking validity of JSON file at %s", context.ro_crate.metadata)
            context.ro_crate.metadata.as_dict()
            return True
        except json.JSONDecodeError as e:
            context.result.add_issue(
                f'RO-Crate file descriptor "{context.rel_fd_path}" is not valid JSON: '
                f"{e.msg} at line {e.lineno}, column {e.colno} (char {e.pos})",
                self,
            )
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("RO-Crate file descriptor is not valid JSON", exc_info=True)
            # The metadata cannot be parsed: abort to avoid false positives downstream.
            context.abort_validation(f"file descriptor is not valid JSON: {e}")
            return False
        except Exception:
            context.result.add_issue(
                f'RO-Crate file descriptor "{context.rel_fd_path}" is not in the correct format', self
            )
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
            return False


@requirement(name="File Descriptor JSON-LD format")
class FileDescriptorJsonLdFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON-LD file
    """

    def __get_remote_context__(self, context_uri: str) -> object:
        raw_data = HttpRequester().get(context_uri, headers={"Accept": "application/ld+json, application/json"})
        if raw_data.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Unable to retrieve the JSON-LD context '{context_uri}'", self)
        logger.debug(f"Retrieved context from {context_uri}")

        content_type = raw_data.headers.get("Content-Type", "")
        is_valid_content_type = "application/ld+json" in content_type or "application/json" in content_type
        if not is_valid_content_type:
            logger.debug(
                f"The retrieved context from {context_uri} "
                f"does not have a Content-Type of application/ld+json or application/json: "
                f"the actual Content-Type is {content_type}. "
            )
            link_header = raw_data.headers.get("Link", "")
            logger.debug(f"Checking Link header for alternate JSON-LD context: {link_header}")
            has_alternate_link = 'rel="alternate"' in link_header and (
                'type="application/ld+json"' in link_header or 'type="application/json"' in link_header
            )

            if has_alternate_link:
                logger.debug(f"Found alternate link for JSON-LD context in Link header: {link_header}")
                match = re.search(r'<([^>]+)>;\s*rel="alternate";\s*type="application/(ld\+json|json)"', link_header)
                if match:
                    alternate_url = match.group(1)
                    if not alternate_url.startswith("http"):
                        alternate_url = urljoin(context_uri, alternate_url)
                    logger.debug(f"Trying to retrieve JSON-LD context from alternate URL: {alternate_url}")
                    raw_data = HttpRequester().get(
                        alternate_url, headers={"Accept": "application/ld+json, application/json"}
                    )
                    if raw_data.status_code != HTTPStatus.OK:
                        raise RuntimeError(
                            f"Unable to retrieve the JSON-LD context from alternate URL '{alternate_url}'", self
                        )
                    logger.debug(f"Retrieved context from alternate URL {alternate_url}")
                    content_type = raw_data.headers.get("Content-Type", "")
                    if "application/ld+json" not in content_type and "application/json" not in content_type:
                        raise RuntimeError(
                            f"The retrieved context from alternate URL {alternate_url} "
                            "does not have a Content-Type of application/ld+json or application/json: "
                            f"the actual Content-Type is {content_type}. ",
                            self,
                        )
                else:
                    logger.debug(f"No valid alternate link found in Link header: {link_header}")
                    raise RuntimeError(
                        f"Unable to retrieve the JSON-LD context from {context_uri} and no valid "
                        f"alternate link found in Link header: {link_header}",
                        self,
                    )
            else:
                logger.debug(f"No alternate link for JSON-LD context found in Link header: {link_header}")
                raise RuntimeError(
                    f"Unable to retrieve the JSON-LD context from {context_uri} "
                    f"and no alternate link found in Link header: {link_header}",
                    self,
                )

        jsonLD = raw_data.json()["@context"]
        assert isinstance(jsonLD, dict)
        return jsonLD

    def __check_remote_context__(self, context_uri: str) -> bool:
        try:
            jsonLD = self.__get_remote_context__(context_uri)
            assert isinstance(jsonLD, dict)
            return True
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    def __check_contexts__(self, context: ValidationContext, jsonld_context: object) -> bool:
        """Get the keys of the context URI"""
        is_valid = True
        # if the context is a string, check if it is a valid URI
        if isinstance(jsonld_context, str) and not self.__check_remote_context__(jsonld_context):
            context.result.add_issue(f'Unable to retrieve the JSON-LD context "{jsonld_context}"', self)
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
        """Check if the file descriptor contains
        the @context property and it is a valid JSON-LD context
        """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            if "@context" not in json_dict:
                context.result.add_issue(
                    f'RO-Crate file descriptor "{context.rel_fd_path}" does not contain a context', self
                )
                return False

            expected_context = "https://w3id.org/ro/crate/1.2/context"
            jsonld_context = json_dict.get("@context")

            def has_expected_context(ctx: object) -> bool:
                if isinstance(ctx, str):
                    return ctx == expected_context
                if isinstance(ctx, list):
                    return expected_context in ctx
                return False

            if not has_expected_context(jsonld_context):
                context.result.add_issue(
                    f'RO-Crate file descriptor "{context.rel_fd_path}" '
                    f'does not reference the required context "{expected_context}"',
                    self,
                )
                return False

            # Check if the context is valid
            return self.__check_contexts__(context, json_dict["@context"])
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    def _check_flat_value_object(self, context: ValidationContext, entity: dict, fail_fast: bool) -> bool:
        """Validate the JSON-LD `@value` object constraints; returns False on violation."""
        result = True
        has_language = "@language" in entity
        has_type = "@type" in entity
        if has_language and has_type:
            context.result.add_issue(
                f'entity "{entity.get("@id", entity)}" is not a valid value object: '
                "@language and @type cannot coexist.",
                self,
            )
            result = False
            if fail_fast:
                return False
        if has_language and not isinstance(entity["@value"], str):
            context.result.add_issue(
                f'entity "{entity.get("@id", entity)}" is not a valid value object: '
                "if @language is present, @value must be a string.",
                self,
            )
            result = False
            if fail_fast:
                return False
        return result

    def _check_flat_non_root_dict(self, context: ValidationContext, entity: dict, fail_fast: bool) -> bool:
        """A non-root dict must be either an `@id` reference or a `@value` object."""
        result = True
        if "@id" in entity and "@value" in entity:
            context.result.add_issue(
                f'entity "{entity.get("@id", entity)}" contains both @id and @value: '
                "an object with an @value represents a value object, which is a literal value such as "
                "a string, number, date, or language-tagged string. This object is not an identifiable "
                "resource, but a simple literal value.",
                self,
            )
            result = False
            if fail_fast:
                return False

        if "@value" in entity:
            if not self._check_flat_value_object(context, entity, fail_fast):
                result = False
                if fail_fast:
                    return False
        # Every remaining entity with more than just @id must be a node object
        elif "@id" not in entity or len(entity) > 1:
            context.result.add_issue(
                f'entity "{entity.get("@id", entity)}" is not a valid node object reference: '
                "it MUST have only @id, but no other properties.",
                self,
            )
            result = False
            if fail_fast:
                return False
        return result

    def _is_entity_flat(self, context: ValidationContext, entity: Any, is_first: bool, fail_fast: bool) -> bool:
        """Recursively check that `entity` corresponds to a flattened JSON-LD object."""
        result = True
        if isinstance(entity, dict):
            if not is_first:
                return self._check_flat_non_root_dict(context, entity, fail_fast)
            for elem in entity.values():
                if not self._is_entity_flat(context, elem, False, fail_fast):
                    result = False
                    if fail_fast:
                        return False
        elif isinstance(entity, list):
            for element in entity:
                if not self._is_entity_flat(context, element, False, fail_fast):
                    result = False
                    if fail_fast:
                        return False
        return result

    @check(name="File Descriptor JSON-LD must be flattened")
    def check_flattened(self, context: ValidationContext) -> bool:
        """Check if the file descriptor is flattened"""
        try:
            fail_fast = bool(context.settings.abort_on_first)
            json_dict = context.ro_crate.metadata.as_dict()
            result = True
            for entity in json_dict["@graph"]:
                if not self._is_entity_flat(context, entity, True, fail_fast):
                    context.result.add_issue(
                        f'RO-Crate file descriptor "{context.rel_fd_path}" '
                        f'is not fully flattened at entity "{entity.get("@id", entity)}"',
                        self,
                    )
                    result = False
                    if fail_fast:
                        return False
            return result
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    @check(name="Validation of the @id property of the file descriptor entities")
    def check_identifiers(self, context: ValidationContext) -> bool:
        """Check if the file descriptor entities have the @id property"""
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            for entity in json_dict["@graph"]:
                if "@id" not in entity:
                    context.result.add_issue(
                        f'Entity "{entity.get("name", None) or entity}" '
                        f'of RO-Crate "{context.rel_fd_path}" '
                        "file descriptor does not contain the @id attribute",
                        self,
                    )
                    return False
            return True
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    @check(name="Validation of the @type property of the file descriptor entities")
    def check_types(self, context: ValidationContext) -> bool:
        """Check if the file descriptor entities have the @type property"""
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            for entity in json_dict["@graph"]:
                if "@type" not in entity:
                    context.result.add_issue(
                        f'Entity "{entity.get("name", None) or entity}" '
                        f'of RO-Crate "{context.rel_fd_path}" '
                        "file descriptor does not contain the @type attribute",
                        self,
                    )
                    return False
            return True
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    @check(name="Validation of unique @id values")
    def check_unique_identifiers(self, context: ValidationContext) -> bool:
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            identifiers = [entity.get("@id") for entity in json_dict.get("@graph", [])]
            duplicates = {i for i in identifiers if i is not None and identifiers.count(i) > 1}
            if duplicates:
                context.result.add_issue(
                    f"Duplicate @id values detected in RO-Crate metadata: {sorted(duplicates)}", self
                )
                return False
            return True
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    def _find_reference_issue(self, value: Any, entity_id: str, identifiers: set, key: str | None = None) -> str | None:
        """
        Return an issue message if `value` references another entity by bare
        string instead of an `{"@id": ...}` object, recursing into lists and
        nested dictionaries; return None when no violation is found.
        """
        if isinstance(value, str):
            if key not in _LITERAL_KEYS and value in identifiers:
                return f"Entity '{entity_id}' references '{value}' as a string; use {{\"@id\": \"{value}\"}}"
            return None
        if isinstance(value, list):
            children: Any = value
        elif isinstance(value, dict):
            if "@value" in value or "@id" in value:
                return None
            children = value.values()
        else:
            return None
        for child in children:
            message = self._find_reference_issue(child, entity_id, identifiers, key)
            if message:
                return message
        return None

    @check(name="Validation of entity references")
    def check_entity_references(self, context: ValidationContext) -> bool:
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            graph = json_dict.get("@graph", [])
            identifiers = {entity.get("@id") for entity in graph if entity.get("@id")}

            for entity in graph:
                entity_id = entity.get("@id")
                for key, value in entity.items():
                    if key in ("@id", "@type", "@context"):
                        continue
                    message = self._find_reference_issue(value, entity_id, identifiers, key)
                    if message:
                        context.result.add_issue(message, self)
                        return False
            return True
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    @check(name="Validation of subject and keyword properties")
    def check_subject_keywords(self, context: ValidationContext) -> bool:
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            graph = json_dict.get("@graph", [])
            for entity in graph:
                entity_id = entity.get("@id")
                if "subject" in entity or "dct:subject" in entity or "dcterms:subject" in entity:
                    context.result.add_issue(f"Entity '{entity_id}' should use schema.org 'about' for subjects", self)
                    return False
                if "keyword" in entity:
                    context.result.add_issue(f"Entity '{entity_id}' should use schema.org 'keywords'", self)
                    return False
            return True
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
        return False

    def __get_context_keys__(self, context: object) -> set:
        """Get the keys of the context URI"""
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
        return set()

    def __get_remote_context_keys__(self, context_uri: str) -> set:
        """Get the keys of the context URI"""

        logger.debug(f"Retrieving context from {context_uri}...")
        # Try to retrieve the context
        raw_data = HttpRequester().get(context_uri, headers={"Accept": "application/ld+json"})
        if raw_data.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Unable to retrieve the JSON-LD context '{context_uri}'")

        logger.debug(f"Retrieved context from {context_uri}")

        # Get the keys of the context
        jsonLD = raw_data.json()
        jsonLD_ctx = jsonLD["@context"]
        if not isinstance(jsonLD_ctx, dict):
            raise TypeError("The context is not a dictionary")
        return set(jsonLD_ctx.keys())

    def __check_entity_keys__(
        self, entity: object, context_keys: set, unexpected_keys: dict[str, int] | None = None
    ) -> dict[str, int]:
        """Check if the entity is in the correct format"""

        def add_unexpected_key(k: str, u_keys: dict) -> None:
            """Add a key to the unexpected keys dictionary"""
            u_keys[k] = u_keys.get(k, 0) + 1

        # Keys that should be skipped
        SKIP_KEYS = {"@id", "@type", "@context", "@value", "@language"}

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
        """Check if the file descriptor is in the **compacted** JSON-LD format"""
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
                    logger.exception("Unexpected error during file descriptor validation")
                context.result.add_issue(str(e), self)
                return False

            unexpected_keys = self.__check_entity_keys__(json_dict.get("@graph", []), context_keys)
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
                            "because the compacted format requires simple terms as keys "
                            "(see https://www.w3.org/TR/json-ld-api/#compaction for more details).",
                            self,
                        )
                    else:
                        context.result.add_issue(
                            f'The {v} occurrence{suffix} of the JSON-LD key "{k}" '
                            f"{'is' if v == 1 else 'are'} not allowed in the compacted format "
                            "because it is not present in the @context of the document",
                            self,
                        )
                return False

            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Unexpected error during file descriptor validation")
            context.result.add_issue(f"Unexpected error: {e}", self)
        return False
