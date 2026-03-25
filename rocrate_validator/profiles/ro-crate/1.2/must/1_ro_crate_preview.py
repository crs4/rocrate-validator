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

from pathlib import Path

from rocrate_validator.utils import log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="RO-Crate Website")
class ROCrateWebsiteChecker(PyFunctionCheck):
    """
    If present, the RO-Crate Website MUST be a valid HTML5 document.
    """

    @check(name="RO-Crate Website HTML5 doctype")
    def check_preview_html(self, context: ValidationContext) -> bool:
        if context.ro_crate.is_detached():
            return True
        preview_path = Path("ro-crate-preview.html")
        if not context.ro_crate.has_file(preview_path):
            return True
        try:
            content = context.ro_crate.get_file_content(preview_path, binary_mode=False)
            if "<!doctype html" in content.lower():
                return True
            context.result.add_issue(
                "ro-crate-preview.html should include an HTML5 doctype", self)
            return False
        except Exception as e:
            context.result.add_issue(
                f"Unable to read ro-crate-preview.html: {str(e)}", self)
            return False
