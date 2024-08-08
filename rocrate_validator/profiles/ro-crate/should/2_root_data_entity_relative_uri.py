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


@requirement(name="RO-Crate Root Data Entity RECOMMENDED value")
class RootDataEntityRelativeURI(PyFunctionCheck):
    """
    The Root Data Entity SHOULD be denoted by the string /
    """

    @check(name="Root Data Entity: RECOMMENDED value")
    def check_relative_uris(self, context: ValidationContext) -> bool:
        """Check if the Root Data Entity is denoted by the string `./` in the file descriptor JSON-LD"""
        try:
            if not context.ro_crate.metadata.get_root_data_entity().id == './':
                context.result.add_error(
                    'Root Data Entity URI is not denoted by the string `./`', self)
                return False
            return True
        except Exception as e:
            context.result.add_error(
                f'Error checking Root Data Entity URI: {str(e)}', self)
            return False
