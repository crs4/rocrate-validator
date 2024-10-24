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


def test_provrc_action_no_resourceusage():
    """\
    Test a Provenance Run Crate where a tool action has no resourceUsage.
    """
    do_entity_test(
        InvalidProvRC().action_no_resourceusage,
        Severity.OPTIONAL,
        False,
        ["Provenance Run Crate tool action MAY"],
        ["A tool action MAY have a resourceUsage"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_action_bad_resourceusage():
    """\
    Test a Provenance Run Crate where a tool action has a resourceUsage that
    does not point to PropertyValue.
    """
    do_entity_test(
        InvalidProvRC().action_bad_resourceusage,
        Severity.REQUIRED,
        False,
        ["Provenance Run Crate tool action MUST"],
        ["If present, resourceUsage MUST point to PropertyValue"],
        profile_identifier="provenance-run-crate"
    )
