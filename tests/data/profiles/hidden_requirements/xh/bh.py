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
from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="B", hidden=True)
class BH(PyFunctionCheck):
    """
    Test requirement outside requirement level folder
    """

    @check(name="B_0")
    def check_b0(self, context: ValidationContext) -> bool:
        """Check B_0: no requirement level"""
        return True

    @check(name="B_1", severity=Severity.REQUIRED)
    def check_b1(self, context: ValidationContext) -> bool:
        """Check B_1: REQUIRED requirement level"""
        return True

    @check(name="B_2", severity=Severity.RECOMMENDED)
    def check_b2(self, context: ValidationContext) -> bool:
        """Check B_2: RECOMMENDED requirement level"""
        return True

    @check(name="B_3", severity=Severity.OPTIONAL)
    def check_b3(self, context: ValidationContext) -> bool:
        """Check B_3: OPTIONAL requirement level"""
        return True
