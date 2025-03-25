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


def test_procrc_application_no_name():
    """\
    Test a Process Run Crate where the application does not have a name.
    """
    do_entity_test(
        InvalidProcRC().application_no_name,
        Severity.RECOMMENDED,
        False,
        ["ProcRC Application"],
        ["The Application SHOULD have a name"],
        profile_identifier="process-run-crate"
    )


def test_procrc_application_no_url():
    """\
    Test a Process Run Crate where the application does not have a url.
    """
    do_entity_test(
        InvalidProcRC().application_no_url,
        Severity.RECOMMENDED,
        False,
        ["ProcRC Application"],
        ["The Application SHOULD have a url"],
        profile_identifier="process-run-crate"
    )


def test_procrc_application_no_version():
    """\
    Test a Process Run Crate where the application does not have a version or
    SoftwareVersion (SoftwareApplication).
    """
    do_entity_test(
        InvalidProcRC().application_no_version,
        Severity.RECOMMENDED,
        False,
        ["ProcRC SoftwareApplication"],
        ["The SoftwareApplication SHOULD have a version or softwareVersion"],
        profile_identifier="process-run-crate"
    )


def test_procrc_application_version_softwareversion():
    """\
    Test a Process Run Crate where the application has both a version and a
    SoftwareVersion (SoftwareApplication).
    """
    do_entity_test(
        InvalidProcRC().application_version_softwareVersion,
        Severity.RECOMMENDED,
        False,
        ["ProcRC SoftwareApplication SingleVersion"],
        ["Process Run Crate SoftwareApplication should not have both version and softwareVersion"],
        profile_identifier="process-run-crate"
    )


def test_procrc_softwaresourcecode_no_version():
    """\
    Test a Process Run Crate where the application does not have a version
    (SoftwareSourceCode).
    """
    do_entity_test(
        InvalidProcRC().softwaresourcecode_no_version,
        Severity.RECOMMENDED,
        False,
        ["ProcRC SoftwareSourceCode or ComputationalWorkflow"],
        ["The SoftwareSourceCode or ComputationalWorkflow SHOULD have a version"],
        profile_identifier="process-run-crate"
    )


def test_procrc_application_id_no_absoluteuri():
    """\
    Test a Process Run Crate where the id of the application is not an
    absolute URI.
    """
    do_entity_test(
        InvalidProcRC().application_id_no_absoluteuri,
        Severity.RECOMMENDED,
        False,
        ["ProcRC SoftwareApplication ID"],
        ["The SoftwareApplication id SHOULD be an absolute URI"],
        profile_identifier="process-run-crate"
    )


def test_procrc_softwareapplication_no_softwarerequirements():
    """\
    Test a Process Run Crate where the SoftwareApplication does not have a
    SoftwareRequirements.
    """
    do_entity_test(
        InvalidProcRC().softwareapplication_no_softwarerequirements,
        Severity.OPTIONAL,
        False,
        ["ProcRC SoftwareApplication MAY"],
        ["The SoftwareApplication MAY have a softwareRequirements that points to a SoftwareApplication"],
        profile_identifier="process-run-crate"
    )


def test_procrc_softwareapplication_bad_softwarerequirements():
    """\
    Test a Process Run Crate where the SoftwareApplication has a
    SoftwareRequirements that does not point to a SoftwareApplication.
    """
    do_entity_test(
        InvalidProcRC().softwareapplication_bad_softwarerequirements,
        Severity.OPTIONAL,
        False,
        ["ProcRC SoftwareApplication MAY"],
        ["The SoftwareApplication MAY have a softwareRequirements that points to a SoftwareApplication"],
        profile_identifier="process-run-crate"
    )
