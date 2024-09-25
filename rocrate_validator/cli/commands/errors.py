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
import textwrap

from rich.console import Console

import rocrate_validator.log as logging
from rocrate_validator.errors import InvalidProfilePath, ProfileNotFound, ProfilesDirectoryNotFound

# Create a logger for this module
logger = logging.getLogger(__name__)


def handle_error(e: Exception, console: Console) -> None:
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
    else:
        error_message = f"\n\n[bold][[red]FAILED[/red]] Unexpected error: {e} !!![/bold]\n"
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception()
        console.print(textwrap.indent("This error may be due to a bug.\n"
                                      "Please report it to the issue tracker "
                                      "along with the following stack trace:\n", ' ' * 9))
        console.print_exception()

    console.print(f"\n\n[bold][[red]ERROR[/red]] {error_message}[/bold]\n", style="white")
    sys.exit(2)
