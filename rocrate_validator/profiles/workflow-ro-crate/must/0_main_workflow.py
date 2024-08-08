# Copyright (c) 2024 CRS4
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

import rocrate_validator.log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Main Workflow file existence")
class MainWorkflowFileExistence(PyFunctionCheck):
    """Checks for main workflow file existence."""

    @check(name="Main Workflow file must exist")
    def check_workflow(self, context: ValidationContext) -> bool:
        """Check if the crate contains the main workflow file."""
        try:
            main_workflow = context.ro_crate.metadata.get_main_workflow()
            if not main_workflow:
                context.result.add_check_issue("main workflow does not exist in metadata file", self)
                return False
            if not main_workflow.is_available():
                context.result.add_check_issue("Main Workflow {main_workflow.id} not found in crate", self)
                return False
            return True
        except ValueError as e:
            context.result.add_check_issue("Unable to check the existence of the main workflow file "
                                           "because the metadata file descriptor doesn't contain a `mainEntity`", self)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False
