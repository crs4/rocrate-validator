import os
import sys
import textwrap
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding

import rocrate_validator.log as logging
from rocrate_validator import services
from rocrate_validator.cli.main import cli, click
from rocrate_validator.colors import get_severity_color
from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.errors import ProfileNotFound, ProfilesDirectoryNotFound
from rocrate_validator.models import (LevelCollection, Severity,
                                      ValidationResult)
from rocrate_validator.utils import URI, get_profiles_path

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
    try:
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
    except ProfilesDirectoryNotFound as e:
        error_message = f"""
        The profile folder could not be located at the specified path: [red]{e.profiles_path}[/red].
        Please ensure that the path is correct and try again.
        """
        console.print(
            f"\n\n[bold][[red]ERROR[/red]] {error_message} !!![/bold]\n", style="white")
        sys.exit(2)
    except ProfileNotFound as e:
        error_message = f"""The profile with the identifier "[red bold]{e.profile_name}[/red bold]" could not be found.
        Please ensure that the profile exists and try again.

        To see the available profiles, run:
        [cyan bold]rocrate-validator profiles list[/cyan bold]
        """
        console.print(
            f"\n\n[bold][[red]ERROR[/red]] {error_message}[/bold]\n", style="white")
        sys.exit(2)
    except Exception as e:
        console.print(
            f"\n\n[bold][[red]FAILED[/red]] Unexpected error: {e} !!![/bold]\n", style="white")
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception()
        console.print(textwrap.indent("This error may be due to a bug.\n"
                      "Please report it to the issue tracker along with the following stack trace:\n", ' ' * 9))
        console.print_exception()
        sys.exit(2)


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
                Padding(f"\n\n[bold][[green]OK[/green]] RO-Crate is [green]valid[/green] !!![/bold]\n\n", (0, 2)),
                style="white",
            )
        else:
            console.print(
                Padding(f"\n\n[bold][[red]FAILED[/red]] RO-Crate is [red]not valid[/red] !!![/bold]\n", (0, 2)),
                style="white",
            )

            console.print(Padding("\n[bold]The following requirements have not meet: [/bold]", (0, 2)), style="white")

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
                console.print(Padding(Markdown(requirement.description), (1, 7)))
                console.print(Padding("[white bold u]  Failed checks  [/white bold u]\n",
                              (0, 8)), style="white bold")

                for check in sorted(result.get_failed_checks_by_requirement(requirement),
                                    key=lambda x: (-x.severity.value, x)):
                    issue_color = get_severity_color(check.level.severity)
                    console.print(
                        Padding(f"[bold][{issue_color}][{check.identifier.center(16)}][/{issue_color}]  [magenta]{check.name}[/magenta][/bold]:", (0, 7)), style="white bold")
                    console.print(Padding(Markdown(check.description), (0, 27)))
                    console.print(Padding("[u]Detected issues[/u]", (0, 8)), style="white bold")
                    for issue in sorted(result.get_issues_by_check(check),
                                        key=lambda x: (-x.severity.value, x)):
                        path = ""
                        if issue.resultPath and issue.value:
                            path = f"of [yellow]{issue.resultPath}[/yellow]"
                        if issue.value:
                            if issue.resultPath:
                                path += "="
                            path += f"\"[green]{issue.value}[/green]\" "  # keep the ending space
                        path = path + "on " + f"[cyan]<{issue.focusNode}>[/cyan]"
                        console.print(
                            Padding(f"- [[red]Violation[/red] {path}]: "
                                    f"{Markdown(issue.message).markup}", (0, 9)), style="white")
                    console.print("\n", style="white")
