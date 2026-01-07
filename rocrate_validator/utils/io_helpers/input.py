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

from __future__ import annotations

import sys
from typing import Optional

from InquirerPy import prompt
from InquirerPy.base.control import Choice
from rich.console import Console

from rocrate_validator.utils import log as logging
from rocrate_validator.models import Profile

# set up logging
logger = logging.getLogger(__name__)


def __get_single_char_win32__(console: Optional[Console] = None, end: str = "\n",
                              message: Optional[str] = None,
                              choices: Optional[list[str]] = None) -> str:
    """
    Get a single character from the console
    """
    import msvcrt

    char = None
    while char is None or (choices and char not in choices):
        if console and message:
            console.print(f"\n{message}", end="")
        try:
            char = msvcrt.getch().decode()
        finally:
            if console:
                console.print(char, end=end if choices and char in choices else "")
        if choices and char not in choices:
            if console:
                console.print(" [bold red]INVALID CHOICE[/bold red]", end=end)
    return char


def __get_single_char_unix__(console: Optional[Console] = None, end: str = "\n",
                             message: Optional[str] = None,
                             choices: Optional[list[str]] = None) -> str:
    """
    Get a single character from the console
    """
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    char = None
    while char is None or (choices and char not in choices):
        if console and message:
            console.print(f"\n{message}", end="")
        try:
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1)
            if char == "\x03":
                raise KeyboardInterrupt
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            if console:
                console.print(char, end=end if choices and char in choices else "")
        if choices and char not in choices:
            if console:
                console.print(" [bold red]INVALID CHOICE[/bold red]", end=end)
    return char


def get_single_char(console: Optional[Console] = None, end: str = "\n",
                    message: Optional[str] = None,
                    choices: Optional[list[str]] = None) -> str:
    """
    Get a single character from the console
    """
    if sys.platform == "win32":
        return __get_single_char_win32__(console, end, message, choices)
    return __get_single_char_unix__(console, end, message, choices)


def multiple_choice(console: Console,
                    choices: list[Profile]):
    """
    Display a multiple choice menu
    """
    # Build the prompt text
    prompt_text = "Please select the profiles to validate the RO-Crate against (<SPACE> to select):"

    # Get the selected option
    question = [
        {
            "type": "checkbox",
            "name": "profiles",
            "message": prompt_text,
            "choices": [Choice(i, f"{choices[i].identifier}: {choices[i].name}") for i in range(0, len(choices))]
        }
    ]
    console.print("\n")
    selected = prompt(question, style={"questionmark": "#ff9d00 bold",
                                       "question": "bold",
                                       "checkbox": "magenta",
                                       "answer": "magenta"},
                      style_override=False)
    logger.debug("Selected profiles: %s", selected)
    return selected["profiles"]
