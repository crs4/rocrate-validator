import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidProcRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_procrc_containerimage_no_additionaltype():
    """\
    Test a Process Run Crate where the ContainerImage has no additionalType.
    """
    do_entity_test(
        InvalidProcRC().containerimage_no_additionaltype,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate ContainerImage SHOULD"],
        ["The ContainerImage SHOULD have an additionalType pointing to <https://w3id.org/ro/terms/workflow-run#DockerImage> or <https://w3id.org/ro/terms/workflow-run#SIFImage>"],
        profile_identifier="process-run-crate"
    )


def test_procrc_containerimage_bad_additionaltype():
    """\
    Test a Process Run Crate where the ContainerImage additionalType does not
    point to one of the allowed values.
    """
    do_entity_test(
        InvalidProcRC().containerimage_bad_additionaltype,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate ContainerImage SHOULD"],
        ["The ContainerImage SHOULD have an additionalType pointing to <https://w3id.org/ro/terms/workflow-run#DockerImage> or <https://w3id.org/ro/terms/workflow-run#SIFImage>"],
        profile_identifier="process-run-crate"
    )


def test_procrc_containerimage_no_registry():
    """\
    Test a Process Run Crate where the ContainerImage has no registry.
    """
    do_entity_test(
        InvalidProcRC().containerimage_no_registry,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate ContainerImage SHOULD"],
        ["The ContainerImage SHOULD have a registry"],
        profile_identifier="process-run-crate"
    )


def test_procrc_containerimage_no_name():
    """\
    Test a Process Run Crate where the ContainerImage has no name.
    """
    do_entity_test(
        InvalidProcRC().containerimage_no_name,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate ContainerImage SHOULD"],
        ["The ContainerImage SHOULD have a name"],
        profile_identifier="process-run-crate"
    )


def test_procrc_containerimage_no_tag():
    """\
    Test a Process Run Crate where the ContainerImage has no tag.
    """
    do_entity_test(
        InvalidProcRC().containerimage_no_tag,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate ContainerImage MAY"],
        ["The ContainerImage MAY have a tag"],
        profile_identifier="process-run-crate"
    )


def test_procrc_containerimage_no_sha256():
    """\
    Test a Process Run Crate where the ContainerImage has no sha256.
    """
    do_entity_test(
        InvalidProcRC().containerimage_no_sha256,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate ContainerImage MAY"],
        ["The ContainerImage MAY have a sha256"],
        profile_identifier="process-run-crate"
    )
