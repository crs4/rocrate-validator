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

"""
RECOMMENDED checks on entity @id values:
  - @id SHOULD NOT use ../ to climb out of the RO-Crate Root
  - International characters SHOULD be native UTF-8, not percent-encoded
  - Named contextual entities (Person, Organization) SHOULD use #-prefixed @id
"""

import re

from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement
from rocrate_validator.utils import log as logging

logger = logging.getLogger(__name__)

# Matches any %XX sequence where XX decodes to a non-ASCII byte (0x80–0xFF).
# These are UTF-8 continuation / leading bytes for multi-byte code-points.
_PCT_NON_ASCII_RE = re.compile(r"%[89A-Fa-f][0-9A-Fa-f]")

# Types for which a non-absolute @id SHOULD start with '#'
_NAMED_ENTITY_TYPES = frozenset({"Person", "Organization"})


@requirement(name="Entity identifier: format recommendations")
class EntityIdentifierFormatChecker(PyFunctionCheck):
    """
    Checks that entity @id values follow RO-Crate 1.2 RECOMMENDED conventions:
    no parent-directory traversal, native UTF-8 for international characters,
    and '#'-prefixed identifiers for named local entities.
    """

    @check(name="Entity identifiers SHOULD NOT use ../", severity=Severity.RECOMMENDED)
    def check_no_parent_traversal(self, context: ValidationContext) -> bool:
        """
        @id paths SHOULD NOT use `../` to climb out of the RO-Crate Root
        (RO-Crate 1.2, JSON-LD appendix).
        """
        result = True
        for entity in context.ro_crate.metadata.as_dict().get("@graph", []):
            entity_id = entity.get("@id", "")
            if "../" in entity_id:
                context.result.add_issue(
                    f"Entity @id '{entity_id}' uses '../' to traverse above the "
                    f"RO-Crate Root; @id paths SHOULD NOT contain '../'",
                    self,
                )
                result = False
                if context.fail_fast:
                    return result
        return result

    @check(
        name="Entity identifiers SHOULD use native UTF-8, not percent-encoding",
        severity=Severity.RECOMMENDED,
    )
    def check_utf8_identifiers(self, context: ValidationContext) -> bool:
        """
        International characters in @id values SHOULD be written in native
        UTF-8 rather than percent-encoded (RO-Crate 1.2, JSON-LD appendix).
        """
        result = True
        for entity in context.ro_crate.metadata.as_dict().get("@graph", []):
            entity_id = entity.get("@id", "")
            if _PCT_NON_ASCII_RE.search(entity_id):
                context.result.add_issue(
                    f"Entity @id '{entity_id}' contains percent-encoded non-ASCII "
                    f"characters; international characters SHOULD be written in "
                    f"native UTF-8 rather than percent-encoded",
                    self,
                )
                result = False
                if context.fail_fast:
                    return result
        return result

    @check(
        name="Named contextual entity @id SHOULD use '#' prefix",
        severity=Severity.RECOMMENDED,
    )
    def check_named_entity_id_format(self, context: ValidationContext) -> bool:
        """
        Named entities such as Person or Organization that are referenced locally
        SHOULD use an @id starting with '#' rather than a bare relative path
        (RO-Crate 1.2, JSON-LD appendix).
        """
        result = True
        for entity in context.ro_crate.metadata.as_dict().get("@graph", []):
            entity_id = entity.get("@id", "")
            raw_type = entity.get("@type", "")
            types = [raw_type] if isinstance(raw_type, str) else raw_type
            if not _NAMED_ENTITY_TYPES.intersection(types):
                continue
            # Absolute IRIs and blank nodes are fine; only flag bare relative paths
            if (
                entity_id.startswith("http://")
                or entity_id.startswith("https://")
                or entity_id.startswith("#")
                or entity_id.startswith("_:")
            ):
                continue
            context.result.add_issue(
                f"Entity @id '{entity_id}' of type '{raw_type}' is a local identifier "
                f"that does not start with '#'; named local entities SHOULD use a "
                f"'#'-prefixed @id (e.g. '#alice')",
                self,
            )
            result = False
            if context.fail_fast:
                return result
        return result
