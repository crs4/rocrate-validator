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

from rocrate_validator.utils import log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Root Data Entity: hasPart coverage")
class RootDataEntityHasPartChecker(PyFunctionCheck):
    """
    Root Data Entity MUST reference all Data Entities directly or indirectly via hasPart.
    """

    @check(name="Root Data Entity: hasPart must cover all Data Entities")
    def check_has_part(self, context: ValidationContext) -> bool:
        try:
            root = context.ro_crate.metadata.get_root_data_entity()
            data_entities = [
                e for e in context.ro_crate.metadata.get_data_entities()
                if not e.has_local_identifier() and e.id != root.id
            ]

            reachable = set()
            stack = []
            root_has_part = root.get_property("hasPart")
            if root_has_part:
                stack.extend(root_has_part if isinstance(root_has_part, list) else [root_has_part])

            while stack:
                current = stack.pop()
                if hasattr(current, "id"):
                    current_id = current.id
                else:
                    continue
                if current_id in reachable:
                    continue
                reachable.add(current_id)
                if hasattr(current, "get_property"):
                    nested = current.get_property("hasPart")
                    if nested:
                        stack.extend(nested if isinstance(nested, list) else [nested])

            missing = [e.id for e in data_entities if e.id not in reachable]
            if missing:
                context.result.add_issue(
                    f"Root Data Entity hasPart does not cover Data Entities: {missing}", self)
                return False
            return True
        except Exception as e:
            context.result.add_issue(
                f"Error checking hasPart coverage: {str(e)}", self)
            return False
