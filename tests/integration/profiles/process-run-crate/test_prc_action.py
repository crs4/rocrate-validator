import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidProcRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_prc_action_no_instrument():
    """\
    Test a Process Run Crate where the action does not have an instrument.
    """
    do_entity_test(
        InvalidProcRC().action_no_instrument,
        Severity.REQUIRED,
        False,
        ["Process Run Crate Action"],
        ["The Action MUST have an instrument property that references the executed tool"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_instrument_bad_type():
    """\
    Test a Process Run Crate where the instrument does not point to a
    SoftwareApplication, SoftwareSourceCode or ComputationalWorkflow.
    """
    do_entity_test(
        InvalidProcRC().action_instrument_bad_type,
        Severity.REQUIRED,
        False,
        ["Process Run Crate Action"],
        ["The Action MUST have an instrument property that references the executed tool"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_not_mentioned():
    """\
    Test a Process Run Crate where the action is not listed in the Root Data
    Entity's mentions.
    """
    do_entity_test(
        InvalidProcRC().action_not_mentioned,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD be referenced from the Root Data Entity via mentions"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_name():
    """\
    Test a Process Run Crate where the action does not have an name.
    """
    do_entity_test(
        InvalidProcRC().action_no_name,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have a name"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_description():
    """\
    Test a Process Run Crate where the action does not have a description.
    """
    do_entity_test(
        InvalidProcRC().action_no_description,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have a description"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_endtime():
    """\
    Test a Process Run Crate where the action does not have an endTime.
    """
    do_entity_test(
        InvalidProcRC().action_no_endtime,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have an endTime in ISO 8601 format"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_bad_endtime():
    """\
    Test a Process Run Crate where the action does not have an endTime.
    """
    do_entity_test(
        InvalidProcRC().action_bad_endtime,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have an endTime in ISO 8601 format"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_agent():
    """\
    Test a Process Run Crate where the action does not have an agent.
    """
    do_entity_test(
        InvalidProcRC().action_no_agent,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have an agent that is a Person or Organization"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_bad_agent():
    """\
    Test a Process Run Crate where the agent is neither a Person nor an
    Organization.
    """
    do_entity_test(
        InvalidProcRC().action_bad_agent,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have an agent that is a Person or Organization"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_result():
    """\
    Test a Process Run Crate where the CreateAction or UpdateAction does not
    have a result.
    """
    do_entity_test(
        InvalidProcRC().action_no_result,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate CreateAction UpdateAction SHOULD"],
        ["The Action SHOULD have a result"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_starttime():
    """\
    Test a Process Run Crate where the action does not have an startTime.
    """
    do_entity_test(
        InvalidProcRC().action_no_starttime,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate Action MAY"],
        ["The Action MAY have a startTime"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_bad_starttime():
    """\
    Test a Process Run Crate where the action does not have an startTime.
    """
    do_entity_test(
        InvalidProcRC().action_bad_starttime,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["If present, the Action startTime SHOULD be in ISO 8601 format"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_error_not_failed_status():
    """\
    Test a Process Run Crate where the action has an error even though its
    actionStatus is not FailedActionStatus.
    """
    do_entity_test(
        InvalidProcRC().action_error_not_failed_status,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action error"],
        ["error SHOULD NOT be specified unless actionStatus is set to FailedActionStatus"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_error_no_status():
    """\
    Test a Process Run Crate where the action has an error even though it has
    no actionStatus.
    """
    do_entity_test(
        InvalidProcRC().action_error_no_status,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action error"],
        ["error SHOULD NOT be specified unless actionStatus is set to FailedActionStatus"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_object():
    """\
    Test a Process Run Crate where the Action does not have an object.
    """
    do_entity_test(
        InvalidProcRC().action_no_object,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate Action MAY"],
        ["The Action MAY have an object"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_actionstatus():
    """\
    Test a Process Run Crate where the Action does not have an actionstatus.
    """
    do_entity_test(
        InvalidProcRC().action_no_actionstatus,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate Action MAY"],
        ["The Action MAY have an actionStatus"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_bad_actionstatus():
    """\
    Test a Process Run Crate where the Action has an invalid actionstatus.
    """
    do_entity_test(
        InvalidProcRC().action_bad_actionstatus,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["If the Action has an actionStatus, it should be http://schema.org/CompletedActionStatus or http://schema.org/FailedActionStatus"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_error():
    """\
    Test a Process Run Crate where the Action does not have an error.
    """
    do_entity_test(
        InvalidProcRC().action_no_error,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate Action MAY have error"],
        ["error MAY be specified if actionStatus is set to FailedActionStatus"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_obj_res_bad_type():
    """\
    Test a Process Run Crate where the Action's object or result does not
    point to a MediaObject, Dataset, Collection, CreativeWork or
    PropertyValue.
    """
    do_entity_test(
        InvalidProcRC().action_obj_res_bad_type,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action object and result types"],
        ["object and result SHOULD point to entities of type MediaObject, Dataset, Collection, CreativeWork or PropertyValue"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_environment():
    """\
    Test a Process Run Crate where the Action does not have an environment.
    """
    do_entity_test(
        InvalidProcRC().action_no_environment,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate Action MAY"],
        ["The Action MAY have an environment"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_bad_environment():
    """\
    Test a Process Run Crate where the Action has an environment that does not
    point to PropertyValues.
    """
    do_entity_test(
        InvalidProcRC().action_bad_environment,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["If the Action has an environment, it should point to entities of type PropertyValue"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_no_containerimage():
    """\
    Test a Process Run Crate where the Action does not have a containerimage.
    """
    do_entity_test(
        InvalidProcRC().action_no_containerimage,
        Severity.OPTIONAL,
        False,
        ["Process Run Crate Action MAY"],
        ["The Action MAY have a containerImage"],
        profile_identifier="process-run-crate"
    )


def test_prc_action_bad_containerimage():
    """\
    Test a Process Run Crate where the Action has a containerImage that does
    not point to a URL or to a ContainerImage object.
    """
    for crate in (InvalidProcRC().action_bad_containerimage_url,
                  InvalidProcRC().action_bad_containerimage_type):
        do_entity_test(
            InvalidProcRC().action_bad_containerimage_url,
            Severity.RECOMMENDED,
            False,
            ["Process Run Crate Action SHOULD"],
            ["If the Action has a containerImage, it should point to a ContainerImage or a URL"],
            profile_identifier="process-run-crate"
        )
