import os
import sys
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.console import Console

from rocrate_validator.constants import DEFAULT_PROFILE_NAME
import rocrate_validator.log as logging

from ... import services
from ...colors import get_severity_color
from ...models import Severity, ValidationResult
from ...utils import get_profiles_path
from ..main import cli, click

# from rich.markdown import Markdown
# from rich.table import Table

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


@cli.command("validate")
@click.argument("rocrate-path", type=click.Path(exists=True), default=".")
@click.option(
    '-nff',
    '--no-fail-fast',
    is_flag=True,
    help="Disable fail fast validation mode",
    default=False,
    show_default=True
)
@click.option(
    "--profiles-path",
    type=click.Path(exists=True),
    default=DEFAULT_PROFILES_PATH,
    show_default=True,
    help="Path containing the profiles files",
)
@click.option(
    "-p",
    "--profile-name",
    type=click.STRING,
    default=DEFAULT_PROFILE_NAME,
    show_default=True,
    help="Name of the profile to use for validation",
)
@click.option(
    '-nh',
    '--disable-profile-inheritance',
    is_flag=True,
    help="Disable inheritance of profiles",
    default=False,
    show_default=True
)
@click.option(
    "-l",
    "--requirement-severity",
    type=click.Choice([s.name for s in Severity], case_sensitive=False),
    default=Severity.REQUIRED.name,
    show_default=True,
    help="Severity of the requirements to validate",
)
@click.option(
    '-lo',
    '--requirement-severity-only',
    is_flag=True,
    help="Validate only the requirements of the specified severity (no requirements with lower severity)",
    default=False,
    show_default=True
)
# @click.option(
#     "-o",
#     "--ontologies-path",
#     type=click.Path(exists=True),
#     default="./ontologies",
#     help="Path containing the ontology files",
# )
@click.pass_context
def validate(ctx,
             profiles_path: Path = DEFAULT_PROFILES_PATH,
             profile_name: str = "ro-crate",
             disable_profile_inheritance: bool = False,
             requirement_severity: str = Severity.REQUIRED.name,
             requirement_severity_only: bool = False,
             rocrate_path: Path = Path("."),
             no_fail_fast: bool = False,
             ontologies_path: Optional[Path] = None):
    """
    [magenta]rocrate-validator:[/magenta] Validate a RO-Crate against a profile
    """
    console: Console = ctx.obj['console']
    # Log the input parameters for debugging
    logger.debug("profiles_path: %s", os.path.abspath(profiles_path))
    logger.debug("profile_name: %s", profile_name)
    logger.debug("requirement_severity: %s", requirement_severity)
    logger.debug("requirement_severity_only: %s", requirement_severity_only)

    logger.debug("disable_inheritance: %s", disable_profile_inheritance)
    logger.debug("rocrate_path: %s", os.path.abspath(rocrate_path))
    logger.debug("no_fail_fast: %s", no_fail_fast)
    logger.debug("fail fast: %s", not no_fail_fast)

    if ontologies_path:
        logger.debug("ontologies_path: %s", os.path.abspath(ontologies_path))
    if rocrate_path:
        logger.debug("rocrate_path: %s", os.path.abspath(rocrate_path))

    # Validate the RO-Crate
    result: ValidationResult = services.validate(
        {
            "profiles_path": profiles_path,
            "profile_name": profile_name,
            "requirement_severity": requirement_severity,
            "requirement_severity_only": requirement_severity_only,
            "inherit_profiles": not disable_profile_inheritance,
            "data_path": Path(rocrate_path).absolute(),
            "ontology_path": Path(ontologies_path).absolute() if ontologies_path else None,
            "abort_on_first": not no_fail_fast
        }
    )

    # Print the validation result
    __print_validation_result__(console, result)

    # using ctx.exit seems to raise an Exception that gets caught below,
    # so we use sys.exit instead.
    sys.exit(0 if result.passed(Severity.RECOMMENDED) else 1)


def __print_validation_result__(
        console: Console,
        result: ValidationResult,
        severity: Severity = Severity.RECOMMENDED):
    """
    Print the validation result
    """
    if result.passed(severity=severity):
        console.print(
            f"\n\n[bold][[green]OK[/green]] RO-Crate is [green]valid[/green] !!![/bold]\n\n",
            style="white",
        )
    else:
        console.print(
            f"\n\n[bold][[red]FAILED[/red]] RO-Crate is [red]not valid[/red] !!![/bold]\n",
            style="white",
        )

        console.print("\n[bold]The following requirements have not meet: [/bold]\n", style="white")

        for requirement in sorted(result.failed_requirements,
                                  key=lambda x: (-x.severity.value, x)):
            issue_color = get_severity_color(requirement.severity)
            console.print(
                Align(f"\n [severity: [{issue_color}]{requirement.severity.name}[/{issue_color}], "
                      f"profile: [magenta bold]{requirement.profile.name }[/magenta bold]]", align="right")
            )
            console.print(
                f"  [bold][cyan][{requirement.order_number}] [u]{requirement.name}[/u][/cyan][/bold]",
                style="white",
            )
            console.print(f"\n{' '*4}{requirement.description}\n", style="white italic")

            console.print(f"{' '*4}Failed checks:\n", style="white bold")
            for check in sorted(result.get_failed_checks_by_requirement(requirement),
                                key=lambda x: (-x.severity.value, x)):
                issue_color = get_severity_color(check.level.severity)
                console.print(
                    f"{' '*4}- "
                    f"[magenta bold]{check.name}[/magenta bold]: {check.description}")
                console.print(f"\n{' '*6}Detected issues:", style="white bold")
                for issue in sorted(result.get_issues_by_check(check),
                                    key=lambda x: (-x.severity.value, x)):
                    console.print(
                        f"{' '*6}- [[red]Violation[/red] of "
                        f"[{issue_color} bold]{issue.check.identifier}[/{issue_color} bold]]: {issue.message}")
                console.print("\n", style="white")
