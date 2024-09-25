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


@requirement(name="Workflow-related files existence")
class WorkflowFilesExistence(PyFunctionCheck):
    """Checks for workflow-related crate files existence."""

    @check(name="Workflow diagram existence")
    def check_workflow_diagram(self, context: ValidationContext) -> bool:
        """Check if the crate contains the workflow diagram."""
        try:
            main_workflow = context.ro_crate.metadata.get_main_workflow()
            image = main_workflow.get_property("image")
            diagram_relpath = image.id if image else None
            if not diagram_relpath:
                context.result.add_error("main workflow does not have an 'image' property", self)
                return False
            if not image.is_available():
                context.result.add_error(f"Workflow diagram '{image.id}' not found in crate", self)
                return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(f"Unexpected error: {e}")
            return False

    @check(name="Workflow description existence")
    def check_workflow_description(self, context: ValidationContext) -> bool:
        """Check if the crate contains the workflow CWL description."""
        try:
            main_workflow = context.ro_crate.metadata.get_main_workflow()
            main_workflow_subject = main_workflow.get_property("subjectOf")
            description_relpath = main_workflow_subject.id if main_workflow_subject else None
            if not description_relpath:
                context.result.add_error("main workflow does not have a 'subjectOf' property", self)
                return False
            if not main_workflow_subject.is_available():
                context.result.add_error(
                    f"Workflow CWL description {main_workflow_subject.id} not found in crate", self)
                return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(f"Unexpected error: {e}")
            return False
