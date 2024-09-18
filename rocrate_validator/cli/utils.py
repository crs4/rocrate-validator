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

import os
import pydoc
import re
import textwrap
from typing import Any, Optional

from rich.console import Console as BaseConsole
from rich.padding import Padding
from rich.pager import Pager
from rich.rule import Rule
from rich.text import Text

from rocrate_validator import log as logging
from rocrate_validator.utils import get_version

# set up logging
logger = logging.getLogger(__name__)


def format_text(text: str,
                initial_indent: int = 0,
                subsequent_indent: int = 0,
                line_width: Optional[int] = None,
                skip_initial_indent: bool = False) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    line_width = line_width or os.get_terminal_size().columns - initial_indent
    if line_width:
        text = textwrap.fill(text, width=line_width, initial_indent=' ' *
                             (initial_indent if not skip_initial_indent else 0),
                             subsequent_indent=' ' * subsequent_indent,
                             break_long_words=False,
                             break_on_hyphens=False)
    else:
        text = textwrap.indent(text, ' ' * initial_indent)
    return text


def get_app_header_rule() -> Text:
    return Padding(Rule(f"\n[bold][cyan]ROCrate Validator[/cyan] (ver. [magenta]{get_version()}[/magenta])[/bold]",
                        style="bold cyan"), (1, 2))


class SystemPager(Pager):
    """Uses the pager installed on the system."""

    def _pager(self, content: str) -> Any:
        return pydoc.pipepager(content, "less -R")

    def show(self, content: str) -> None:
        """Use the same pager used by pydoc."""
        self._pager(content)


class Console(BaseConsole):
    """Rich console that can be disabled."""

    def __init__(self, *args, disabled: bool = False,  **kwargs):
        super().__init__(*args, **kwargs)
        self.disabled = disabled

    def print(self, *args, **kwargs):
        if not self.disabled:
            super().print(*args, **kwargs)
