
import sys

import rich_click as click
from rich.console import Console

import rocrate_validator.log as logging
from rocrate_validator.errors import ProfilesDirectoryNotFound
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
        logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)
        # If no subcommand is provided, invoke the default command
        if ctx.invoked_subcommand is None:
            # If no subcommand is provided, invoke the default command
            from .commands.validate import validate
            ctx.invoke(validate)

    except ProfilesDirectoryNotFound as e:
        error_message = f"""
        The profile folder could not be located at the specified path: [red]{e.profiles_path}[/red]. 
        Please ensure that the path is correct and try again.
        """
        console.print(
            f"\n\n[bold][[red]ERROR[/red]] {error_message} !!![/bold]\n", style="white")
        sys.exit(2)
    except Exception as e:
        console.print(
            f"\n\n[bold][[red]FAILED[/red]] Unexpected error: {e} !!![/bold]\n", style="white")
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception()
        console.print("""
            This error may be due to a bug. Please report it to the issue tracker
            along with the following stack trace:
            """)
        sys.exit(2)


if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(f"An unexpected error occurred: {e}")
        exit(2)
