import logging
import os

from rich.align import Align

from ... import services
from ...colors import get_severity_color
from ...models import Severity, ValidationResult
from .. import cli, click, console

# from rich.markdown import Markdown
# from rich.table import Table


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
            "\n\n[bold][[green]OK[/green]] RO-Crate is [green]valid[/green] !!![/bold]\n\n",
            style="white",
        )
    else:
        console.print(
            "\n\n[bold][[red]FAILED[/red]] RO-Crate is [red]not valid[/red] !!![/bold]\n",
            style="white",
        )

        console.print("\n[bold]The following requirements have not meet: [/bold]\n", style="white")

        for requirement in result.failed_requirements:
            issue_color = get_severity_color(requirement.severity)
            console.print(
                Align(f" [severity: [{issue_color}]{requirement.severity.name}[/{issue_color}], "
                      f"profile: [magenta]{requirement.profile.name }[/magenta]]", align="right")
            )
            console.print(
                f"  [bold][magenta][{requirement.order_number}] [u]{requirement.name}[/u][/magenta][/bold]",
                style="white",
            )
            console.print(f"\n{' '*4}{requirement.description}\n", style="white italic")

            console.print(f"{' '*4}Failed checks:\n", style="white bold")
            for check in result.get_failed_checks_by_requirement(requirement):
                issue_color = get_severity_color(check.severity)
                console.print(
                    f"{' '*4}- "
                    f"[magenta]{check.name}[/magenta]: {check.description}")
                console.print(f"\n{' '*6}Detected issues:", style="white bold")
                for issue in check.get_issues():
                    console.print(
                        f"{' '*6}- [[{issue_color}]Violation[/{issue_color}] of "
                        f"[magenta]{issue.check.identifier}[/magenta]]: {issue.message}")
                console.print("\n", style="white")
