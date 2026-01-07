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

from typing import Any, Optional

from rich.console import Console, ConsoleOptions, RenderResult

from rocrate_validator.utils import log as logging
from rocrate_validator.models import ValidationResult, ValidationStatistics

from .. import BaseOutputFormatter
from .formatters import (ValidationResultTextOutputFormatter,
                         ValidationStatisticsTextOutputFormatter)

# set up logging
logger = logging.getLogger(__name__)


class TextOutputFormatter(BaseOutputFormatter):

    def __init__(self, data: Optional[Any] = None):
        super().__init__(data)
        self.add_type_formatter(ValidationResult, ValidationResultTextOutputFormatter)
        self.add_type_formatter(ValidationStatistics, ValidationStatisticsTextOutputFormatter)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield from super().__rich_console__(console, options)
