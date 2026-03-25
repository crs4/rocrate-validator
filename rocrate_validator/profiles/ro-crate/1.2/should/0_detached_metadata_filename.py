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


@requirement(name="Detached RO-Crate metadata filename")
class DetachedMetadataFilenameChecker(PyFunctionCheck):
    """
    Detached RO-Crate metadata files SHOULD be named ${prefix}-ro-crate-metadata.json
    """

    @check(name="Detached RO-Crate: metadata filename")
    def check_filename(self, context: ValidationContext) -> bool:
        try:
            if not context.ro_crate.is_detached():
                return True
            if not context.ro_crate.uri.is_local_file():
                return True
            filename = context.ro_crate.uri.as_path().name
            if filename.endswith("-ro-crate-metadata.json"):
                return True
            if filename == "ro-crate-metadata.json":
                context.result.add_issue(
                    "Detached RO-Crate metadata file SHOULD be named ${prefix}-ro-crate-metadata.json", self)
                return False
            return True
        except Exception as e:
            context.result.add_issue(
                f"Error checking detached metadata filename: {str(e)}", self)
            return False
