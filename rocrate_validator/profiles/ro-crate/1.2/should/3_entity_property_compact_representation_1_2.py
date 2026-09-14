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

# pylint: disable=invalid-name  # profile filename uses digit prefix (load-order convention)

from rocrate_validator.errors import ROCrateMetadataNotFoundError
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.jsonld import find_singleton_property_arrays

logger = logging.getLogger(__name__)


@requirement(name="Entity properties compact representation")
class EntityPropertyCompactRepresentation(PyFunctionCheck):
    """
    Single-element arrays used for entity properties SHOULD be unpacked to a
    single value in compacted RO-Crate 1.2 JSON-LD.
    """

    @check(name="Entity properties SHOULD use single values rather than singleton arrays")
    def check_singleton_property_arrays(self, context: ValidationContext) -> bool:
        """Check the RO-Crate 1.2 recommendation for singleton property arrays."""
        try:
            findings = find_singleton_property_arrays(context.ro_crate.metadata.as_dict())
        except ROCrateMetadataNotFoundError as error:
            logger.debug("Skipping singleton property array check: metadata descriptor is not available (%s)", error)
            return True
        except (AttributeError, TypeError, ValueError) as error:
            # Required format checks report malformed metadata structure.
            logger.debug("Skipping singleton property array check: metadata cannot be inspected (%s)", error)
            return True

        result = True
        for entity_id, property_name in findings:
            context.result.add_issue(
                f'Entity "{entity_id}" property "{property_name}" SHOULD be represented as a single value, '
                "not a singleton array, according to the RO-Crate 1.2 JSON-LD recommendation",
                self,
                violatingEntity=entity_id,
                violatingProperty=property_name,
                violatingPropertyValue="singleton array",
            )
            result = False
            if context.fail_fast:
                return result
        return result
