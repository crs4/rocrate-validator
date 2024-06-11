import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidMainWorkflow
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_main_workflow_bad_type():
    """\
    Test a Workflow RO-Crate where the main workflow has an incorrect type.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_bad_type,
        Severity.REQUIRED,
        False,
        ["Main Workflow definition"],
        ["The Main Workflow must have types File, SoftwareSourceCode, ComputationalWorfklow"],
        profile_name="workflow-ro-crate"
    )


def test_main_workflow_no_lang():
    """\
    Test a Workflow RO-Crate where the main workflow does not have a
    programmingLanguage property.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_lang,
        Severity.REQUIRED,
        False,
        ["Main Workflow definition"],
        ["The Main Workflow must refer to its language via programmingLanguage"],
        profile_name="workflow-ro-crate"
    )


def test_main_workflow_no_image():
    """\
    Test a Workflow RO-Crate where the main workflow does not have an
    image property.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_image,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The Crate MAY contain a Main Workflow Diagram; if present it MUST be referred to via 'image'"],
        profile_name="workflow-ro-crate"
    )


def test_main_workflow_no_cwl_desc():
    """\
    Test a Workflow RO-Crate where the main workflow does not have an
    CWL description.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_cwl_desc,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The Crate MAY contain a Main Workflow CWL Description; if present it MUST be referred to via 'subjectOf'"],
        profile_name="workflow-ro-crate"
    )


def test_main_workflow_cwl_desc_bad_type():
    """\
    Test a Workflow RO-Crate where the main workflow has a CWL description
    but of the wrong type.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_cwl_desc_bad_type,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The CWL Description type must be File, SoftwareSourceCode, HowTo"],
        profile_name="workflow-ro-crate"
    )


def test_main_workflow_cwl_desc_no_lang():
    """\
    Test a Workflow RO-Crate where the main workflow has a CWL description
    but the description has no programmingLanguage.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_cwl_desc_no_lang,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The CWL Description SHOULD have a language of https://w3id.org/workflowhub/workflow-ro-crate#cwl"],
        profile_name="workflow-ro-crate"
    )


def test_main_workflow_file_existence():
    """\
    Test a Workflow RO-Crate where the main workflow file is not in the crate.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_files,
        Severity.REQUIRED,
        False,
        ["Main Workflow file existence"],
        ["Main Workflow", "not found in crate"],
        profile_name="workflow-ro-crate"
    )


# The following two tests pass only if run singularly

# def test_workflow_diagram_file_existence():
#     """\
#     Test a Workflow RO-Crate where the workflow diagram file is not in the
#     crate.
#     """
#     do_entity_test(
#         InvalidMainWorkflow().main_workflow_no_files,
#         Severity.OPTIONAL,
#         False,
#         ["Workflow-related files existence"],
#         ["Workflow diagram", "not found in crate"],
#         profile_name="workflow-ro-crate"
#     )


# def test_workflow_description_file_existence():
#     """\
#     Test a Workflow RO-Crate where the workflow CWL description file is not in
#     the crate.
#     """
#     do_entity_test(
#         InvalidMainWorkflow().main_workflow_no_files,
#         Severity.OPTIONAL,
#         False,
#         ["Workflow-related files existence"],
#         ["Workflow CWL description", "not found in crate"],
#         profile_name="workflow-ro-crate"
#     )
