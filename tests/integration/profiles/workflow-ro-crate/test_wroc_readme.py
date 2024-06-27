import logging

from rocrate_validator.models import Severity
from tests.ro_crates import WROCInvalidReadme
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_wroc_readme_not_about_crate():
    """\
    Test a Workflow RO-Crate where the README.md is not about the crate.
    """
    do_entity_test(
        WROCInvalidReadme().wroc_readme_not_about_crate,
        Severity.RECOMMENDED,
        False,
        ["README.md properties"],
        ["The README.md SHOULD be about the crate"],
        profile_identifier="workflow-ro-crate"
    )


def test_wroc_readme_wrong_encoding_format():
    """\
    Test a Workflow RO-Crate where the README.md has the wrong encodingFormat..
    """
    do_entity_test(
        WROCInvalidReadme().wroc_readme_wrong_encoding_format,
        Severity.RECOMMENDED,
        False,
        ["README.md properties"],
        ["The README.md SHOULD have text/markdown as its encodingFormat"],
        profile_identifier="workflow-ro-crate"
    )
