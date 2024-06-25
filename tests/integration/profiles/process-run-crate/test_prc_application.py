import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidProcRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_prc_application_no_name():
    """\
    Test a Process Run Crate where the application does not have a name.
    """
    do_entity_test(
        InvalidProcRC().application_no_name,
        Severity.RECOMMENDED,
        False,
        ["ProcRC Application"],
        ["The Application SHOULD have a name"],
        profile_name="s_process-run-crate"
    )


def test_prc_application_no_url():
    """\
    Test a Process Run Crate where the application does not have a url.
    """
    do_entity_test(
        InvalidProcRC().application_no_url,
        Severity.RECOMMENDED,
        False,
        ["ProcRC Application"],
        ["The Application SHOULD have a url"],
        profile_name="s_process-run-crate"
    )


def test_prc_application_no_version():
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
        profile_name="s_process-run-crate"
    )


def test_prc_application_version_softwareversion():
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
        profile_name="s_process-run-crate"
    )


def test_prc_softwaresourcecode_no_version():
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
        profile_name="s_process-run-crate"
    )


def test_prc_application_id_no_absoluteuri():
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
        profile_name="s_process-run-crate"
    )
