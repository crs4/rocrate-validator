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

import rocrate_validator.log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Data Entity: RECOMMENDED resource availability")
class DataEntityRecommendedChecker(PyFunctionCheck):
    """
    Data Entities with absolute URI paths SHOULD be available
    at the time of RO-Crate creation
    """

    @check(name="Data Entity: RECOMMENDED resource availability")
    def check_availability(self, context: ValidationContext) -> bool:
        """
        Check the availability of the Data Entity with absolute URI paths
        are available at the time of RO-Crate creation
        """
        result = True
        for entity in [
                _ for _ in context.ro_crate.metadata.get_data_entities(exclude_web_data_entities=True)
                if _.has_absolute_path()]:
            assert entity.id is not None, "Entity has no @id"
            try:
                if not entity.is_available():
                    context.result.add_issue(
                        f'Data Entity {entity.id} is not available', self)
                    result = False
            except Exception as e:
                context.result.add_issue(
                    f'Web-based Data Entity {entity.id} is not available: {e}', self)
                result = False
            if not result and context.fail_fast:
                return result
        return result
