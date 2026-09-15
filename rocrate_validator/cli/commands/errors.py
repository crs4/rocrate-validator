# Copyright (c) 2024-2026 CRS4
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
import traceback

from rich.console import Console
from rich.markup import escape
from rich.padding import Padding
from rich.panel import Panel
from rich.syntax import Syntax

from rocrate_validator.errors import BadSyntaxError, InvalidProfilePath, ProfileNotFound, ProfilesDirectoryNotFound


def handle_error(e: Exception, console: Console, *, debug: bool = False) -> None:
    error_message = ""
    if isinstance(e, ProfilesDirectoryNotFound):
        error_message = f"""
        The profile folder could not be located at the specified path: [red]{e.profiles_path}[/red].
        Please ensure that the path is correct and try again.
        """
    elif isinstance(e, ProfileNotFound):
        error_message = f"""The profile with the identifier "[red bold]{e.profile_name}[/red bold]" could not be found.
        Please ensure that the profile exists and try again.

        To see the available profiles, run:
        [cyan bold]rocrate-validator profiles list[/cyan bold]
        """
    elif isinstance(e, InvalidProfilePath):
        error_message = f"""The profile path "[red bold]{e.profile_path}[/red bold]" is not valid.
        Please ensure that the profile exists and try again.

        To see the available profiles, run:
        [cyan bold]rocrate-validator profiles list[/cyan bold]
        """
    elif isinstance(e, BadSyntaxError):
        location = _format_syntax_error_location(e)
        error_message = (
            "The validation profile could not be parsed.\n"
            f"Path: {escape(e.path)}\n"
            f"Reason: {location}[red]{escape(_summarize_syntax_error(e.message))}[/red]"
        )
    else:
        error_message = f"Unexpected error: {escape(str(e))}"

    console.print(f"\n\n[bold][[red]ERROR[/red]] {error_message}[/bold]\n", style="white")
    if debug:
        _print_debug_traceback(e, console)
    sys.exit(2)


def _summarize_syntax_error(message: str) -> str:
    """Return the useful part of a parser error without its source dump."""
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("Bad syntax"):
            return line.partition(" at ^ in:")[0]
    return lines[0] if lines else "Unknown syntax error"


def _format_syntax_error_location(error: BadSyntaxError) -> str:
    """Format the parser location when the underlying parser provided one."""
    location = []
    if error.line is not None:
        location.append(f"line {error.line}")
    if error.character is not None:
        location.append(f"character {error.character}")
    return f"[orange1]{escape(', '.join(location))}[/orange1] --> " if location else ""


def _print_debug_traceback(error: Exception, console: Console) -> None:
    """Render a safe, readable traceback for exceptions from third-party parsers."""
    traceback_text = "".join(traceback.format_exception(type(error), error, error.__traceback__)).rstrip()
    if console.no_color or not getattr(console, "interactive", True):
        console.print(f"Debug traceback:\n{traceback_text}", markup=False)
        return

    console.print(
        Padding(
            Panel(
                Syntax(traceback_text, "pytb", theme="ansi_dark", line_numbers=False, word_wrap=True),
                title="[bold yellow]Debug traceback[/bold yellow]",
                title_align="left",
                border_style="yellow",
                padding=(1, 1, 1, 1),
            ),
            (1, 1, 0, 1),
        )
    )
