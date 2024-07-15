import os
import sys
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown

import rocrate_validator.log as logging
from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER

from ... import services
from ...colors import get_severity_color
from ...models import LevelCollection, Severity, ValidationResult
from ...utils import URI, get_profiles_path
from ..main import cli, click

# from rich.markdown import Markdown
# from rich.table import Table

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


def validate_uri(ctx, param, value):
    """
    Validate if the value is a path or a URI
    """
    if value:
        try:
            # parse the value to extract the scheme
            uri = URI(value)
            if not uri.is_remote_resource() and not uri.is_local_directory() and not uri.is_local_file():
                raise click.BadParameter(f"Invalid RO-Crate URI \"{value}\": "
                                         "it MUST be a local directory or a ZIP file (local or remote).", param=param)
            if not uri.is_available():
                raise click.BadParameter("RO-crate URI not available", param=param)
        except ValueError as e:
            logger.debug(e)
            raise click.BadParameter("Invalid RO-crate path or URI", param=param)

    return value


@cli.command("validate")
@click.argument("rocrate-uri", callback=validate_uri, default=".")
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
    "--profile-identifier",
    type=click.STRING,
    default=DEFAULT_PROFILE_IDENTIFIER,
    show_default=True,
    help="Identifier of the profile to use for validation",
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
@click.option(
    '--no-paging',
    is_flag=True,
    help="Disable paging",
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
             profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER,
             disable_profile_inheritance: bool = False,
             requirement_severity: str = Severity.REQUIRED.name,
             requirement_severity_only: bool = False,
             rocrate_uri: Path = ".",
             no_fail_fast: bool = False,
             ontologies_path: Optional[Path] = None,
             no_paging: bool = False):
    """
    [magenta]rocrate-validator:[/magenta] Validate a RO-Crate against a profile
    """
    console: Console = ctx.obj['console']
    # Get the no_paging flag
    enable_pager = not no_paging
    # Log the input parameters for debugging
    logger.debug("profiles_path: %s", os.path.abspath(profiles_path))
    logger.debug("profile_identifier: %s", profile_identifier)
    logger.debug("requirement_severity: %s", requirement_severity)
    logger.debug("requirement_severity_only: %s", requirement_severity_only)

    logger.debug("disable_inheritance: %s", disable_profile_inheritance)
    logger.debug("rocrate_uri: %s", rocrate_uri)
    logger.debug("no_fail_fast: %s", no_fail_fast)
    logger.debug("fail fast: %s", not no_fail_fast)

    if ontologies_path:
        logger.debug("ontologies_path: %s", os.path.abspath(ontologies_path))
    if rocrate_uri:
        logger.debug("rocrate_path: %s", os.path.abspath(rocrate_uri))

    # Validate the RO-Crate
    result: ValidationResult = services.validate(
        {
            "profiles_path": profiles_path,
            "profile_identifier": profile_identifier,
            "requirement_severity": requirement_severity,
            "requirement_severity_only": requirement_severity_only,
            "inherit_profiles": not disable_profile_inheritance,
            "data_path": rocrate_uri,
            "ontology_path": Path(ontologies_path).absolute() if ontologies_path else None,
            "abort_on_first": not no_fail_fast
        }
    )

    # Print the validation result
    __print_validation_result__(console, result, result.context.requirement_severity, enable_pager=enable_pager)

    # using ctx.exit seems to raise an Exception that gets caught below,
    # so we use sys.exit instead.
    sys.exit(0 if result.passed(LevelCollection.get(requirement_severity).severity) else 1)


def __print_validation_result__(
        console: Console,
        result: ValidationResult,
        severity: Severity = Severity.RECOMMENDED,
        enable_pager: bool = True):
    """
    Print the validation result
    """
    with console.pager(styles=True) if enable_pager else console:
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
                    f"  [bold][cyan][{requirement.order_number}] [u]{Markdown(requirement.name).markup}[/u][/cyan][/bold]",
                    style="white",
                )
                console.print(f"\n{' '*4}{Markdown(requirement.description).markup}\n", style="white italic")

                console.print(f"{' '*4}[cyan u]Failed checks[/cyan u]:\n", style="white bold")
                for check in sorted(result.get_failed_checks_by_requirement(requirement),
                                    key=lambda x: (-x.severity.value, x)):
                    issue_color = get_severity_color(check.level.severity)
                    console.print(
                        f"{' '*4}- "
                        f"[magenta bold]{check.name}[/magenta bold]: {Markdown(check.description).markup}")
                    console.print(f"\n{' '*6}[u]Detected issues[/u]:", style="white bold")
                    for issue in sorted(result.get_issues_by_check(check),
                                        key=lambda x: (-x.severity.value, x)):
                        path = ""
                        if issue.resultPath and issue.value:
                            path = f"on [yellow]{issue.resultPath}[/yellow]"
                        if issue.value:
                            if issue.resultPath:
                                path += "="
                            path += f"\"[green]{issue.value}[/green]\""
                        if issue.focusNode:
                            path = path + " of " if len(path) > 0 else " on " + f"[cyan]<{issue.focusNode}>[/cyan]"
                        console.print(
                            f"{' ' * 6}- [[red]Violation[/red] of "
                            f"[{issue_color} bold]{issue.check.identifier}[/{issue_color} bold]{path}]: "
                            f"{Markdown(issue.message).markup}",)
                    console.print("\n", style="white")
