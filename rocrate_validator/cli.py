import logging
import os

import click
from rich.console import Console
from rocrate_validator.errors import CheckValidationError, SHACLValidationError
from rocrate_validator.service import validate as validate_rocrate

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
def validate(shapes_path: str, ontologies_path: str,  rocrate_path: str):
    """
    Validate a RO-Crate using SHACL shapes as constraints.
    * this command might be the only one needed for the CLI.
    ??? merge this command with the main command ?
    """

    # Print the input parameters
    logger.debug("shapes_path: %s", os.path.abspath(shapes_path))
    logger.debug("rocrate-path: %s", os.path.abspath(rocrate_path))
    logger.debug("ontologies_path: %s", os.path.abspath(ontologies_path))

    try:

        # Validate the RO-Crate
        result = validate_rocrate(
            rocrate_path=os.path.abspath(rocrate_path),
            shapes_path=os.path.abspath(shapes_path),
            # ontologies_path=os.path.abspath(ontologies_path),
        )

        # Print the validation result
        logger.debug("Validation conforms: %s" % result)
        console.print(
            "\n\n[bold]\[[green]OK[/green]] RO-Crate is valid!!![/bold]\n\n",
            style="white",
        )

    except Exception as e:
        console.print(
            "\n\n[bold]\[[red]FAILED[/red]] RO-Crate is not valid!!![/bold]\n",
            style="white",
        )
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception()
        if isinstance(e, CheckValidationError):
            console.print(
                f"Check [bold][red]{e.check.name}[/red][/bold] failed: ")
            console.print(f" -> {str(e)}\n\n", style="white")
        elif isinstance(e, SHACLValidationError):
            _log_validation_result_(e.result)
        else:
            console.print("Error: ", style="red", end="")
            console.print(f" -> {str(e)}\n\n", style="white")
        console.print("\n\n", style="white")


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
