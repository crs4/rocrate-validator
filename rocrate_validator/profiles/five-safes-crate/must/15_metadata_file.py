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

import re

import rocrate_validator.utils.log as logging
from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="RO-Crate context version")
class FileDescriptorContextVersion(PyFunctionCheck):
    """The RO-Crate metadata file MUST include the RO-Crate context version 1.2
    (or later minor version) in `@context`"""

    @check(name="RO-Crate context version", severity=Severity.REQUIRED)
    def test_existence(self, context: ValidationContext) -> bool:
        """
        The RO-Crate metadata file MUST include the RO-Crate context version 1.2
        (or later minor version) in `@context`
        """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            context_value = json_dict["@context"]
            pattern = re.compile(
                r"https://w3id\.org/ro/crate/1\.[2-9](-DRAFT)?/context"
            )
            passed = True
            if isinstance(context_value, list):
                if not any(
                    pattern.match(item)
                    for item in context_value
                    if isinstance(item, str)
                ):
                    passed = False
            else:
                if not pattern.match(context_value):
                    passed = False
            if not passed:
                context.result.add_issue(
                    "The RO-Crate metadata file MUST include the RO-Crate context "
                    "version 1.2 (or later minor version) in `@context`",
                    self,
                )
            return passed

        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return True
