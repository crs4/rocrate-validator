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


def test_provrc_conformsto_no_provrc():
    """\
    Test a Provenance Run Crate where the root data entity does not conformsTo
    the Provenance Run Crate profile.
    """
    do_entity_test(
        InvalidProvRC().conformsto_no_provrc,
        Severity.REQUIRED,
        False,
        ["Provenance Run Crate Root Data Entity"],
        ["The Root Data Entity MUST reference a CreativeWork entity with an "
         "@id URI that is consistent with the versioned permalink of the "
         "Provenance Run Crate profile"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_conformsto_no_wfrc():
    """\
    Test a Provenance Run Crate where the root data entity does not conformsTo
    the Workflow Run Crate profile.
    """
    do_entity_test(
        InvalidProvRC().conformsto_no_wfrc,
        Severity.RECOMMENDED,
        False,
        ["Provenance Run Crate Root Data Entity SHOULD"],
        ["The Root Data Entity SHOULD reference CreativeWork entities "
         "corresponding to the Process Run Crate, Workflow Run Crate and "
         "Workflow RO-Crate profiles"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_conformsto_no_wroc():
    """\
    Test a Provenance Run Crate where the root data entity does not conformsTo
    the Workflow RO-Crate profile.
    """
    do_entity_test(
        InvalidProvRC().conformsto_no_wroc,
        Severity.RECOMMENDED,
        False,
        ["Provenance Run Crate Root Data Entity SHOULD"],
        ["The Root Data Entity SHOULD reference CreativeWork entities "
         "corresponding to the Process Run Crate, Workflow Run Crate and "
         "Workflow RO-Crate profiles"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_conformsto_no_procrc():
    """\
    Test a Provenance Run Crate where the root data entity does not conformsTo
    the Process Run Crate profile.
    """
    do_entity_test(
        InvalidProvRC().conformsto_no_procrc,
        Severity.RECOMMENDED,
        False,
        ["Provenance Run Crate Root Data Entity SHOULD"],
        ["The Root Data Entity SHOULD reference CreativeWork entities "
         "corresponding to the Process Run Crate, Workflow Run Crate and "
         "Workflow RO-Crate profiles"],
        profile_identifier="provenance-run-crate"
    )
