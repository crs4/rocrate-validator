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


@requirement(name="Root Data Entity: identifier PropertyValue")
class RootIdentifierPropertyChecker(PyFunctionCheck):
    """
    If the Root Data Entity identifier references a PropertyValue, it MUST include value.
    """

    @check(name="Root Data Entity: identifier PropertyValue value")
    def check_identifier_values(self, context: ValidationContext) -> bool:
        try:
            root = context.ro_crate.metadata.get_root_data_entity()
            identifiers = root.get_property("identifier")
            if identifiers is None:
                return True
            identifiers = identifiers if isinstance(identifiers, list) else [identifiers]
            for identifier in identifiers:
                if not hasattr(identifier, "has_type"):
                    continue
                if not identifier.has_type("PropertyValue"):
                    continue
                if not identifier.get_property("value"):
                    context.result.add_issue(
                        "PropertyValue identifiers MUST include a `value`", self)
                    return False
            return True
        except Exception as e:
            context.result.add_issue(
                f"Error checking identifier PropertyValue: {str(e)}", self)
            return False
