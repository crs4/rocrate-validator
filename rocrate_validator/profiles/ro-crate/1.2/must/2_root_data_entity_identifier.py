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

import re

from rocrate_validator.utils import log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Root Data Entity: identifier")
class RootDataEntityIdentifierChecker(PyFunctionCheck):
    """
    In an attached RO-Crate, the Root Data Entity @id MUST be ./ or an absolute URI.
    """

    @check(name="Root Data Entity: REQUIRED value")
    def check_identifier(self, context: ValidationContext) -> bool:
        try:
            if context.ro_crate.is_detached():
                return True
            root_entity = context.ro_crate.metadata.get_root_data_entity()
            if root_entity.id == './':
                return True
            if re.match(r"^[A-Za-z][A-Za-z0-9+\.-]*:", root_entity.id):
                return True
            context.result.add_issue(
                'Root Data Entity @id MUST be `./` or an absolute URI for attached RO-Crates', self)
            return False
        except Exception as e:
            context.result.add_issue(
                f'Error checking Root Data Entity @id: {str(e)}', self)
            return False
