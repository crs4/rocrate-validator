import logging
import os

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

from . import services
from .colors import get_severity_color
from .models import Severity, ValidationResult

# set up logging
logger = logging.getLogger(__name__)


# Create a Rich Console instance for enhanced output
console = Console()


@click.group(invoke_without_command=True)
@click.rich_config(help_config=click.RichHelpConfiguration(use_rich_markup=True))
@click.option(
    '--debug',
    is_flag=True,
    help="Enable debug logging",
    default=False
)
@click.pass_context
def cli(ctx, debug: bool = False):
    # Set the log level
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
    # If no subcommand is provided, invoke the default command
    if ctx.invoked_subcommand is None:
        # If no subcommand is provided, invoke the default command
        ctx.invoke(validate)


@cli.group("profiles")
def profiles():
    """
    [magenta]rocrate-validator:[/magenta] Manage profiles
    """
    pass


@profiles.command("list")
@click.option(
    "-p",
    "--profiles-path",
    type=click.Path(exists=True),
    default="./profiles",
    show_default=True,
    help="Path containing the profiles files",
)
@click.pass_context
def list_profiles(ctx, profiles_path: str = "./profiles"):
    """
    List available profiles
    """
    profiles = services.get_profiles(profiles_path=profiles_path)
    # console.print("\nAvailable profiles:", style="white bold")
    console.print("\n", style="white bold")

    table = Table(show_header=True,
                  title="Available profiles",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=True,
                  caption="(*) Number of requirements by severity")

    # Define columns
    table.add_column("Name", style="magenta bold")
    table.add_column("Description", style="white italic")
    table.add_column("Requirements (*)", style="white")

    # Add data to the table
    for profile_name, profile in profiles.items():
        # Count requirements by severity
        requirements = {}
        logger.debug("Requirements: %s", requirements)
        for req in profile.requirements:
            if not requirements.get(req.type.name, None):
                requirements[req.type.name] = 0
            requirements[req.type.name] += 1
        requirements = ", ".join(
            [f"[bold][{get_severity_color(severity)}]{severity}: "
             f"{count}[/{get_severity_color(severity)}][/bold]"
             for severity, count in requirements.items() if count > 0])

        # Add the row to the table
        table.add_row(profile_name, Markdown(profile.description.strip()), requirements)
        table.add_row()

    # Print the table
    console.print(table)


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
    default="./profiles",
    show_default=True,
    help="Path containing the profiles files",
)
@click.option(
    "-p",
    "--profile-name",
    type=click.STRING,
    default="ro-crate",
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
    "--requirement-level",
    type=click.Choice(["MUST", "SHOULD", "MAY"], case_sensitive=False),
    default="MUST",
    show_default=True,
    help="Level of the requirements to validate",
)
@click.option(
    '-lo',
    '--requirement-level-only',
    is_flag=True,
    help="Validate only the requirements of the specified level (no levels with lower severity)",
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
             profiles_path: str = "./profiles",
             profile_name: str = "ro-crate",
             disable_profile_inheritance: bool = False,
             requirement_level: str = "MUST",
             requirement_level_only: bool = False,
             rocrate_path: str = ".",
             no_fail_fast: bool = False,
             ontologies_path: str = None):
    """
    [magenta]rocrate-validator:[/magenta] Validate a RO-Crate against a profile
    """
    # Log the input parameters for debugging
    logger.debug("profiles_path: %s", os.path.abspath(profiles_path))
    logger.debug("profile_name: %s", profile_name)
    logger.debug("requirement_level: %s", requirement_level)
    logger.debug("requirement_level_only: %s", requirement_level_only)

    logger.debug("disable_inheritance: %s", disable_profile_inheritance)
    logger.debug("rocrate_path: %s", os.path.abspath(rocrate_path))
    logger.debug("no_fail_fast: %s", no_fail_fast)
    logger.debug("fail fast: %s", not no_fail_fast)

    if ontologies_path:
        logger.debug("ontologies_path: %s", os.path.abspath(ontologies_path))
    if rocrate_path:
        logger.debug("rocrate_path: %s", os.path.abspath(rocrate_path))

    try:

        # Validate the RO-Crate
        result: ValidationResult = services.validate(
            profiles_path=profiles_path,
            profile_name=profile_name,
            requirement_level=requirement_level,
            requirement_level_only=requirement_level_only,
            disable_profile_inheritance=disable_profile_inheritance,
            rocrate_path=os.path.abspath(rocrate_path),
            ontologies_path=os.path.abspath(
                ontologies_path) if ontologies_path else None,
            abort_on_first=not no_fail_fast
        )

        # Print the validation result
        __print_validation_result__(result)

    except Exception as e:
        console.print(
            f"\n\n[bold]\[[red]FAILED[/red]] Unexpected error: {e} !!![/bold]\n",
            style="white",
        )
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception()


def __print_validation_result__(
        result: ValidationResult,
        severity: Severity = Severity.WARNING):
    """
    Print the validation result
    """
    if result.passed(severity=severity):
        console.print(
            "\n\n[bold]\[[green]OK[/green]] RO-Crate is [green]valid[/green] !!![/bold]\n\n",
            style="white",
        )
    else:
        console.print(
            "\n\n[bold]\[[red]FAILED[/red]] RO-Crate is [red]not valid[/red] !!![/bold]\n",
            style="white",
        )

        for check in result.get_failed_checks():
            # TODO: Add color related to the requirement level associated with the check
            issue_color = get_severity_color(check.severity)
            console.print(
                f" -> [bold][magenta]{check.name}[/magenta] check [red]failed[/red][/bold]"
                f" (severity: [{issue_color}]{check.severity.name}[/{issue_color}])",
                style="white",
            )
            console.print(f"{' '*4}{check.description}\n", style="white italic")
            console.print(f"{' '*4}Detected issues:", style="white bold")
            for issue in check.get_issues():
                console.print(
                    f"{' '*4}- [[{issue_color}]{issue.severity.name}[/{issue_color}] "
                    f"[magenta]{issue.code}[/magenta]]: {issue.message}",
                    style="white")
            console.print("\n", style="white")


if __name__ == "__main__":
    cli()
