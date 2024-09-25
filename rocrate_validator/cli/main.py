# Copyright (c) 2024 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

import rich_click as click

import rocrate_validator.log as logging
from rocrate_validator.cli.utils import Console, SystemPager
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
    '-y',
    '--no-interactive',
    is_flag=True,
    help="Disable interactive mode",
    default=False
)
@click.option(
    '--disable-color',
    is_flag=True,
    help="Disable colored console output",
    default=False
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, version: bool, disable_color: bool, no_interactive: bool):
    ctx.ensure_object(dict)

    # determine if the console is interactive
    interactive = sys.stdout.isatty() and not no_interactive

    console = Console(no_color=disable_color or not interactive)
    # pass the console to subcommands through the click context, after configuration
    ctx.obj['console'] = console
    ctx.obj['pager'] = SystemPager()
    ctx.obj['interactive'] = interactive

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
        else:
            logger.debug("Command invoked: %s", ctx.invoked_subcommand)
    except Exception as e:
        console.print(
            f"\n\n[bold][[red]FAILED[/red]] Unexpected error: {e} !!![/bold]\n", style="white")
        console.print("""This error may be due to a bug.
                      Please report it to the issue tracker
            along with the following stack trace:
            """)
        console.print_exception()
        sys.exit(2)


if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(f"An unexpected error occurred: {e}")
        exit(2)
