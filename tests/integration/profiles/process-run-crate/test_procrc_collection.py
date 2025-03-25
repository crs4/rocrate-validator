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

import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidProcRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_procrc_collection_not_mentioned():
    """\
    Test a Process Run Crate where the collection is not listed in the Root
    Data Entity's mentions.
    """
    do_entity_test(
        InvalidProcRC().collection_not_mentioned,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Collection SHOULD"],
        ["The Collection SHOULD be referenced from the Root Data Entity via mentions"],
        profile_identifier="process-run-crate"
    )


def test_procrc_collection_no_haspart():
    """\
    Test a Process Run Crate where the collection does not have a hasPart.
    """
    do_entity_test(
        InvalidProcRC().collection_no_haspart,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Collection SHOULD"],
        ["The Collection SHOULD have a hasPart"],
        profile_identifier="process-run-crate"
    )


def test_procrc_collection_no_mainentity():
    """\
    Test a Process Run Crate where the collection does not have a mainEntity.
    """
    do_entity_test(
        InvalidProcRC().collection_no_mainentity,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Collection SHOULD"],
        ["The Collection SHOULD have a mainEntity"],
        profile_identifier="process-run-crate"
    )
