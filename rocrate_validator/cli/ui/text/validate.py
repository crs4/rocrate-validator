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

from typing import Any, Callable, Optional

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.utils.io_helpers.output.pager import SystemPager
from rocrate_validator.utils.io_helpers.output.text import TextOutputFormatter
from rocrate_validator.utils.io_helpers.output.text.layout.report import ValidationReportLayout
from rocrate_validator.models import (ValidationResult, ValidationSettings,
                                      ValidationStatistics)

# set up logging
logger = logging.getLogger(__name__)


class ValidationCommandView:
    """
    A class to handle the validation command view
    """

    def __init__(self,
                 validation_settings: Optional[ValidationSettings],
                 interactive: bool = True,
                 no_paging: bool = False,
                 pager: Optional[SystemPager] = None,
                 console: Optional[Console] = None):
        self.console = console or Console()
        self.interactive = interactive
        self.pager = pager if not no_paging else None
        # reference to the validation settings
        self.validation_settings = validation_settings
        # reference to the report layout
        self._report_layout: Optional[ValidationReportLayout] = None

        # Register text output formatter
        self.console.register_formatter(TextOutputFormatter())

        logger.debug("ValidationCommandView initialized with console: %s", self.console)

    @property
    def report_layout(self) -> ValidationReportLayout:
        """
        Get the current report layout

        Returns:
            The current report layout
        """
        if self._report_layout is None:
            self._report_layout = ValidationReportLayout(
                console=self.console,
                settings=self.validation_settings
            )

        return self._report_layout

    def show_validation_progress(self, validation_command: Callable) -> Any:
        """
        Show validation progress using a progress bar

        Args:
            validate_command: The validation command to execute

        Returns:
            The result of the validation command
        """
        logger.debug("Starting validation with progress bar")

        result = self.report_layout.live(
            lambda: validation_command(
                self.validation_settings,
                subscribers=[self.report_layout, self.report_layout.progress_monitor]
            )
        )
        logger.debug("Validation completed  with result: %s", result)
        return result

    def display_validation_statistics(self, statistics: ValidationStatistics) -> None:
        """
        Display the validation statistics

        Args:
            statistics: The validation statistics
        """
        assert statistics is not None, "Validation statistics must be provided"

        with (self.console.pager(pager=self.pager, styles=not self.console.no_color)
              if self.pager else self.console):
            self.console.print(statistics)

    def display_validation_result(self, result: ValidationResult) -> None:
        """
        Display the validation report layout

        Args:
            result: The validation result
        """
        assert result is not None, "Validation result must be provided"

        logger.debug("Displaying validation result")

        with (self.console.pager(pager=self.pager, styles=not self.console.no_color)
              if self.pager else self.console):
            self.console.print(result)
