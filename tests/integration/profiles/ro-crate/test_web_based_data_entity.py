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

import logging

from rocrate_validator import models
from tests.ro_crates import InvalidDataEntity
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


#  Global set up the paths
paths = InvalidDataEntity()


def test_no_recommended_sdDatePublished():
    """Test a web based data entity without a recommended sdDatePublished property."""
    do_entity_test(
        paths.no_sdDatePublished,
        models.Severity.RECOMMENDED,
        False,
        ["Web-based Data Entity: RECOMMENDED properties"],
        ["Web-based Data Entities SHOULD have "
         "a `sdDatePublished` property to indicate when the absolute URL was accessed"]
    )


def test_invalid_recommended_sdDatePublished(invalid_datetime):
    """Test a web based data entity with an invalid sdDatePublished property."""
    do_entity_test(
        paths.invalid_sdDatePublished,
        models.Severity.RECOMMENDED,
        False,
        ["Web-based Data Entity: RECOMMENDED properties"],
        ["Web-based Data Entities SHOULD have "
         "a `sdDatePublished` property to indicate when the absolute URL was accessed"],
        rocrate_entity_patch={"https://sort-and-change-case.cwl": {"datePublished": invalid_datetime}}
    )
