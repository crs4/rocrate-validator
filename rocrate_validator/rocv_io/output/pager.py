from rich.pager import Pager


import pydoc
from typing import Any


class SystemPager(Pager):
    """Uses the pager installed on the system."""

    def _pager(self, content: str) -> Any:
        return pydoc.pipepager(content, "less -R -K")

    def show(self, content: str) -> None:
        """Use the same pager used by pydoc."""
        self._pager(content)
