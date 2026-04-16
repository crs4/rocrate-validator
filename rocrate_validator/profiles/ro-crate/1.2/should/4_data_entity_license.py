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

# ==================================================================
# NOTE
# ==================================================================
#
# The RO-Crate 1.2 specification (section on Licensing) states:
#
#   "Data Entities with different license SHOULD have own license property"
#   (requirement L4 / P2.2)
#
# This requirement is inherently non-actionable in its strict formulation
# because there is no way for a validator to determine whether a Data
# Entity's content *should* be under a different license than the Root
# Data Entity's.  The validator can only observe three states:
#
#   1. A Data Entity declares a `license` identical to the Root's.
#      This is redundant (the entity already inherits the Root license)
#      but not incorrect.
#
#   2. A Data Entity declares a `license` different from the Root's.
#      This is the case the spec explicitly encourages.
#
#   3. A Data Entity does not declare `license`.  It inherits the Root
#      license, which is the default and perfectly acceptable.
#
# While this cross-entity comparison *could* be expressed as a SHACL
# shape using a SPARQL constraint, doing so would produce a validation
# failure that affects the overall validation result.  The intent here
# is purely advisory: the redundant declaration is not an error, it is
# a style improvement suggestion that should not cause the crate to
# fail validation.  By implementing this as a Python PyFunctionCheck
# that only logs a warning (without adding a validation issue), the
# check provides actionable feedback to authors without penalising
# valid crates.

from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils import log as logging

logger = logging.getLogger(__name__)


def _resolve_license_id(license_value) -> str:
    """
    Resolve a license property value to its @id string.

    The `license` property may be:
      - a string (e.g. "https://creativecommons.org/licenses/by/4.0/")
      - a dict with @id (e.g. {"@id": "https://creativecommons.org/licenses/by/4.0/"})
      - an ROCrateEntity object (which has an .id attribute)
      - a list containing any of the above
      - None

    Returns the @id string, or the string value, or empty string if
    unresolvable.
    """
    if license_value is None:
        return ""
    if isinstance(license_value, list):
        items = [_resolve_license_id(item) for item in license_value]
        return ",".join(item for item in items if item)
    if isinstance(license_value, str):
        return license_value
    if hasattr(license_value, "id"):
        return license_value.id
    if isinstance(license_value, dict):
        return license_value.get("@id", "")
    return str(license_value)


@requirement(name="Data Entity: SHOULD NOT redundantly declare the Root license")
class DataEntityLicenseDivergenceChecker(PyFunctionCheck):
    """
    Data Entities that declare a ``license`` property identical to the
    Root Data Entity's license are redundantly overriding the inherited
    license.  The declaration is not incorrect, but it is unnecessary:
    by default, all Data Entities inherit the Root Data Entity's license.

    This check logs a warning for each such redundant declaration,
    suggesting that the property can be removed.  It does **not** add
    a validation issue, so the crate still passes validation.

    Data Entities with a *different* license from the Root are explicitly
    encouraged by the spec and produce no warning.  Data Entities with
    no ``license`` property also produce no warning — they correctly
    inherit the Root license.
    """

    @check(name="Data Entity SHOULD NOT redundantly declare the Root license",
           severity=Severity.RECOMMENDED)
    def check_license_divergence(self, context: ValidationContext) -> bool:
        root_entity = None
        try:
            root_entity = context.ro_crate.metadata.get_root_data_entity()
        except Exception:
            return True
        if root_entity is None:
            return True

        root_license_raw = root_entity.get_property("license")
        if root_license_raw is None:
            return True

        root_license_id = _resolve_license_id(root_license_raw)
        if not root_license_id:
            return True

        for entity in context.ro_crate.metadata.get_data_entities():
            if entity.id == root_entity.id:
                continue
            entity_license_raw = entity.get_property("license")
            if entity_license_raw is None:
                continue

            entity_license_id = _resolve_license_id(entity_license_raw)
            if not entity_license_id:
                continue

            if entity_license_id == root_license_id:
                logger.warning(
                    "Data Entity '%s' declares a `license` property that is "
                    "identical to the Root Data Entity's license ('%s'); "
                    "this is redundant because Data Entities inherit the Root "
                    "license by default.  Remove the `license` property or "
                    "change it to a different license if the content requires "
                    "one.",
                    entity.id, root_license_id)
        return True
