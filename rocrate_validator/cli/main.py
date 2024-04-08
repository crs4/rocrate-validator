import logging
import sys

import rich_click as click
from rich.console import Console

from rocrate_validator.config import configure_logging
from rocrate_validator.utils import get_version

# set up logging
logger = logging.getLogger(__name__)

__all__ = ["cli", "click"]


@click.group(invoke_without_command=True)
@click.rich_config(help_config=click.RichHelpConfiguration(use_rich_markup=True))
@click.option(
    '--debug',
    is_flag=True,
    help="Enable debug logging",
    default=False
)
@click.option(
    '-v',
    '--version',
    is_flag=True,
    help="Show the version of the rocrate-validator package",
    default=False
)
@click.option(
    '--disable-color',
    is_flag=True,
    help="Disable colored console output",
    default=False
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, version: bool, disable_color: bool):
    ctx.ensure_object(dict)
    console = Console(no_color=disable_color)
    # pass the console to subcommands through the click context, after configuration
    ctx.obj['console'] = console

    try:
        # If the version flag is set, print the version and exit
        if version:
            console.print(
                f"[bold]rocrate-validator [cyan]{get_version()}[/cyan][/bold]")
            sys.exit(0)
        # Set the log level
        if debug:
            configure_logging(level=logging.DEBUG)
        else:
            configure_logging(level=logging.WARNING)
        # If no subcommand is provided, invoke the default command
        if ctx.invoked_subcommand is None:
            # If no subcommand is provided, invoke the default command
            from .commands.validate import validate
            ctx.invoke(validate)
    except Exception as e:
        console.print(
            f"\n\n[bold][[red]FAILED[/red]] Unexpected error: {e} !!![/bold]\n", style="white")
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception()
        sys.exit(2)


if __name__ == "__main__":
    try:
        cli()
    except Exception:
        exit(2)
