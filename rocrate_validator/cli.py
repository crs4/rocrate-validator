import logging
import os

import click
from rich.console import Console

from rocrate_validator.errors import CheckValidationError, SHACLValidationError
from rocrate_validator.service import validate as validate_rocrate

from .checks import Severity
from .colors import get_severity_color
from .models import ValidationResult

# set up logging
logger = logging.getLogger(__name__)


# Create a Rich Console instance for enhanced output
console = Console()


@click.group(invoke_without_command=True)
@click.option(
    '--debug',
    is_flag=True,
    help="Enable debug logging",
    default=False
)
@click.option(
    "-s",
    "--shapes-path",
    type=click.Path(exists=True),
    default="./shapes",
    help="Path containing the shapes files",
)
# @click.option(
#     "-o",
#     "--ontologies-path",
#     type=click.Path(exists=True),
#     default="./ontologies",
#     help="Path containing the ontology files",
# )
@click.argument("rocrate-path", type=click.Path(exists=True), default=".")
@click.pass_context
def cli(ctx, debug, shapes_path, ontologies_path=None, rocrate_path="."):
    # Set the log level
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
    # If no subcommand is provided, invoke the default command
    if ctx.invoked_subcommand is None:
        # If no subcommand is provided, invoke the default command
        ctx.invoke(validate, shapes_path=shapes_path,
                   ontologies_path=ontologies_path,
                   rocrate_path=rocrate_path)


@cli.command("validate")
# ??? is it relevant ?
@click.option(
    '-x',
    '--fail-fast',
    is_flag=True,
    help="Fail fast",
    default=True
)
def validate(shapes_path: str, ontologies_path: str = None,
             rocrate_path: str = ".", fail_fast: bool = True):
    """
    Validate a RO-Crate using SHACL shapes as constraints.
    * this command might be the only one needed for the CLI.
    ??? merge this command with the main command ?
    """

    # Log the input parameters for debugging
    if shapes_path:
        logger.debug("shapes_path: %s", os.path.abspath(shapes_path))
    if ontologies_path:
        logger.debug("ontologies_path: %s", os.path.abspath(ontologies_path))
    if rocrate_path:
        logger.debug("ontologies_path: %s", os.path.abspath(rocrate_path))

    try:

        # Validate the RO-Crate
        result: ValidationResult = validate_rocrate(
            rocrate_path=os.path.abspath(rocrate_path),
            shapes_path=os.path.abspath(shapes_path) if shapes_path else None,
            ontologies_path=os.path.abspath(
                ontologies_path) if ontologies_path else None,
        )

        # Print the validation result
        __print_validation_result__(result)

    except Exception as e:
        console.print(
            "\n\n[bold]\[[red]FAILED[/red]] Unexpected error !!![/bold]\n",
            style="white",
        )
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception(e)
        # if isinstance(e, CheckValidationError):
        #     console.print(
        #         f"Check [bold][red]{e.check.name}[/red][/bold] failed: ")
        #     console.print(f" -> {str(e)}\n\n", style="white")
        # elif isinstance(e, SHACLValidationError):
        #     _log_validation_result_(e.result)
        # else:
        #     console.print("Error: ", style="red", end="")
        #     console.print(f" -> {str(e)}\n\n", style="white")
        # console.print("\n\n", style="white")


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

        for issue in result.get_issues(severity=severity):
            issue_color = get_severity_color(issue.severity)
            console.print(
                f" -> [bold][magenta]{issue.check.name}[/magenta] check [red]failed[/red][/bold]",
                style="white",
            )
            console.print(f"{' '*4}{issue.check.description}\n", style="white italic")
            console.print(f"{' '*4}Detected issues:", style="white bold")
            console.print(
                f"{' '*4}- [[{issue_color}]{issue.severity.name}[/{issue_color}] "
                f"[magenta]{issue.code}[/magenta]]: {issue.message}\n\n",
                style="white")


def _log_validation_result_(result: bool):
    # Print the number of violations
    logger.debug("* Number of violations: %s" % len(result.violations))

    console.print("\n[bold]** %s validation errors: [/bold]" %
                  len(result.violations))

    # Print the violations
    count = 0
    for v in result.violations:
        count += 1
        console.print(
            "\n -> [red][bold]Violation "
            f"{count}[/bold][/red]: {v.resultMessage}",
            style="white",
        )
        print(" - resultSeverity: %s" % v.resultSeverity)
        print(" - focusNode: %s" % v.focusNode)
        print(" - resultPath: %s" % v.resultPath)
        print(" - value: %s" % v.value)
        print(" - resultMessage: %s" % v.resultMessage)
        print(" - sourceConstraintComponent: %s" % v.sourceConstraintComponent)
        try:
            if v.sourceShape:
                print(" - sourceShape: %s" % v.sourceShape)
                print(" - sourceShape.name: %s" % v.sourceShape.name)
                print(" - sourceShape.description: %s" %
                      v.sourceShape.description)
                print(" - sourceShape.path: %s" % v.sourceShape.path)
                print(" - sourceShape.nodeKind: %s" % v.sourceShape.nodeKind)
        except Exception as e:
            print(f"Error getting source shape: {e}")
        print("\n")


if __name__ == "__main__":
    cli()
