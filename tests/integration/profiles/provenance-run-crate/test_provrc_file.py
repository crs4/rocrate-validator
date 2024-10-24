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


def test_provrc_environment_file_no_encodingformat():
    """\
    Test a Provenance Run Crate where an environment file has no
    encodingFormat.
    """
    do_entity_test(
        InvalidProvRC().environment_file_no_encodingformat,
        Severity.RECOMMENDED,
        False,
        ["Provenance Run Crate build instructions file SHOULD"],
        ["the environment file SHOULD have an encodingFormat"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_environment_file_no_conformsto():
    """\
    Test a Provenance Run Crate where an environment file has no conformsTo.
    """
    do_entity_test(
        InvalidProvRC().environment_file_no_conformsto,
        Severity.RECOMMENDED,
        False,
        ["Provenance Run Crate build instructions file SHOULD"],
        ["the environment file SHOULD have a conformsTo"],
        profile_identifier="provenance-run-crate"
    )
