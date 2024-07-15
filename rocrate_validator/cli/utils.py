import os
import re
import textwrap
from typing import Optional

from rich.padding import Padding
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
    return Padding(Rule(f"\n[bold][green]ROCrate Validator[/green] (ver. [magenta]{get_version()}[/magenta])[/bold]"), (1, 1))
