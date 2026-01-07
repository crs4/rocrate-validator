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

from typing import Optional

from rich.console import Console as BaseConsole

from rocrate_validator.utils import log as logging

from . import BaseOutputFormatter, OutputFormatter

logger = logging.getLogger(__name__)


class Console(BaseConsole):
    """Rich console that can be disabled."""

    def __init__(self, *args, disabled: bool = False, interactive: bool = True,
                 formatters: dict[type, OutputFormatter] = None, **kwargs):
        force_jupyter = kwargs.pop("force_jupyter", None)
        if force_jupyter is None:
            force_jupyter = False if self.__jupyter_environment__() else None
        super().__init__(*args, force_jupyter=force_jupyter, **kwargs)
        self.disabled = disabled
        self.interactive = interactive
        self._formatters = {}
        self._formatters_opts: dict[type, BaseOutputFormatter] = {}
        # Register provided formatters if any
        if formatters:
            for type_, formatter in formatters.items():
                self.register_formatter(formatter, type_)

    def __jupyter_environment__(self) -> bool:
        from rocrate_validator.cli.utils import running_in_jupyter
        return running_in_jupyter()

    def register_formatter(self, formatter: OutputFormatter, type_: Optional[type] = None):
        if type_ is None and not isinstance(formatter, BaseOutputFormatter):
            raise ValueError("type_ must be provided if formatter is not a BaseOutputFormatter")
        if isinstance(formatter, BaseOutputFormatter):
            for t, f in formatter.get_type_formatters().items():
                self._formatters[t] = f
        else:
            self._formatters[type_] = formatter

    def __format_data__(self, obj, *args, **kwargs):
        formatter = self._formatters.get(type(obj))
        if formatter:
            return formatter(obj)
        else:
            return obj

    def print(self, obj, *args, **kwargs):
        if not self.disabled:
            out = self.__format_data__(obj, *args, **kwargs)
            super().print(out, *args, **kwargs)
