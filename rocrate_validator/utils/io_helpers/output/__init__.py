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

from typing import TYPE_CHECKING, Any, Optional, Protocol, cast

from rich.console import ConsoleOptions, RenderResult

from rocrate_validator.utils import log as logging

if TYPE_CHECKING:
    # The formatters render to the application's Console subclass (which adds
    # ``interactive``/disabling behaviour); typing the protocol against it keeps
    # the concrete formatters' ``__rich_console__`` overrides compatible.
    from rocrate_validator.utils.io_helpers.output.console import Console

# set up logging
logger = logging.getLogger(__name__)


class OutputFormatter(Protocol):
    """Protocol for output formatters."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        pass


class BaseOutputFormatter(OutputFormatter):

    def __init__(self, data: Optional[Any] = None):
        # Formatters are registered as classes (instantiated with the data to
        # render), so the map values are formatter types, not instances.
        self._fmap: dict[type, type[OutputFormatter]] = {}
        self._data = data

    def add_type_formatter(self, data_type: type, formatter: type[OutputFormatter]):
        """Register a formatter for a specific data type."""
        self._fmap[data_type] = formatter

    def get_type_formatter(self, data_type: type) -> type[OutputFormatter]:
        """Retrieve the formatter for a specific data type."""
        formatter = self._fmap.get(data_type)
        if not formatter:
            raise NotImplementedError(f"No formatter registered for type: {data_type.__name__}")
        return formatter

    def get_data_formatter(self, data: Any) -> type[OutputFormatter]:
        """Retrieve the formatter for a specific data type."""
        data_type = type(data)
        formatter = self._fmap.get(data_type)
        if not formatter:
            raise NotImplementedError(f"No formatter registered for type: {data_type.__name__}")
        return formatter

    def get_type_formatters(self) -> dict[type, type[OutputFormatter]]:
        """Retrieve all registered formatters."""
        return dict(self._fmap)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        if self._data is None:
            raise ValueError("No data provided for formatting.")
        formatter = self.get_data_formatter(self._data)
        if not formatter:
            yield self._data
        else:
            # ``formatter`` is a formatter class instantiated with the data to render.
            yield from cast(Any, formatter)(self._data).__rich_console__(console, options)
