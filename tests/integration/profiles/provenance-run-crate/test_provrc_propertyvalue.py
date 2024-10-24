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

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidProvRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_provrc_propertyvalue_no_unitcode():
    """\
    Test a Provenance Run Crate where a PropertyValue does not have a
    unitCode.
    """
    do_entity_test(
        InvalidProvRC().propertyvalue_no_unitcode,
        Severity.RECOMMENDED,
        False,
        ["Provenance Run Crate resource usage PropertyValue SHOULD"],
        ["A PropertyValue used to represent resourceUsage SHOULD have a unitCode"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_propertyvalue_no_propertyid():
    """\
    Test a Provenance Run Crate where a PropertyValue does not have a
    propertyID.
    """
    do_entity_test(
        InvalidProvRC().propertyvalue_no_propertyid,
        Severity.REQUIRED,
        False,
        ["Provenance Run Crate resource usage PropertyValue MUST"],
        ["A PropertyValue used to represent resourceUsage MUST have a propertyID"],
        profile_identifier="provenance-run-crate"
    )
