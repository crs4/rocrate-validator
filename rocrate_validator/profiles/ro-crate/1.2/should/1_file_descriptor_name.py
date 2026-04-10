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


@requirement(name="File Descriptor naming convention")
class FileDescriptorExistence(PyFunctionCheck):
    """
    If stored in a file, SHOULD be named ${prefix}-ro-crate-metadata.json, where the variable ${prefix} 
    is a human readable version of the dataset’s ID or name.
    """

    @check(name="Detached RO-Crate file descriptor RECOMMENDED naming convention")
    def test_detached_descriptor_filename(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor of a Detached RO-Crate exists and is named according to the convention.
        In a Detached RO-Crate, the file descriptor SHOULD be named `{prefix}-ro-crate-metadata.json`,
        where `{prefix}` is a human readable version of the dataset’s ID or name.
        """
        # context.result.add_issue(
        #     'In a detached RO-Crate, the metadata descriptor filename MUST be `ro-crate-metadata.json` or `ro-crate-metadata.yaml`', self)
        # return False
        if context.settings.metadata_only:
            logger.debug("Skipping file descriptor existence check in metadata-only mode")
            return True
        if not context.ro_crate.has_descriptor():
            message = f'file descriptor "{context.rel_fd_path}" is not present'
            context.result.add_issue(message, self)
            return False
        assert context.ro_crate.is_detached(), "File descriptor naming convention check is only applicable to detached RO-Crates"
        if context.ro_crate.is_detached():
            # Check if the filename follows the convention
            fd_filename = context.ro_crate.get_descriptor_path()
            if fd_filename and not (fd_filename.name.endswith("-ro-crate-metadata.json") or fd_filename.name.endswith("-ro-crate-metadata.yaml")):
                context.result.add_issue(
                    'In a detached RO-Crate, the metadata descriptor filename '
                    'SHOULD be named according to the convention `{prefix}-ro-crate-metadata.json` ',
                    self)
                return False
        return True
