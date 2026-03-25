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


@requirement(name="Contact point for authors or publishers")
class ContactPointChecker(PyFunctionCheck):
    """
    At least one author or publisher referenced from the Root Data Entity SHOULD have a contactPoint.
    """

    @check(name="Contact point presence")
    def check_contact_point(self, context: ValidationContext) -> bool:
        try:
            root = context.ro_crate.metadata.get_root_data_entity()
            candidates = []
            for prop in ("author", "publisher"):
                value = root.get_property(prop)
                if value is None:
                    continue
                values = value if isinstance(value, list) else [value]
                candidates.extend(values)
            if not candidates:
                return True
            for entity in candidates:
                if hasattr(entity, "get_property") and entity.get_property("contactPoint"):
                    return True
            context.result.add_issue(
                "At least one author or publisher SHOULD have a contactPoint", self)
            return False
        except Exception as e:
            context.result.add_issue(
                f"Error checking contactPoint: {str(e)}", self)
            return False
