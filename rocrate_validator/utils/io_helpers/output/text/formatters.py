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

from rich.align import Align
from rich.console import ConsoleOptions, RenderResult
from rich.markdown import Markdown
from rich.padding import Padding

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.colors import get_severity_color
from rocrate_validator.utils.io_helpers.output.text.layout.report import \
    ValidationReportLayout
from rocrate_validator.models import ValidationResult, ValidationStatistics

from .. import OutputFormatter
from ..console import Console

# set up logging
logger = logging.getLogger(__name__)


class ValidationResultTextOutputFormatter(OutputFormatter):

    def __init__(self, validation_result: ValidationResult):
        self._validation_result = validation_result

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        result = self._validation_result

        # Print validation details
        # Print the list of failed requirements
        yield Padding("\n[bold]The following requirements have not been met: [/bold]", (0, 2))
        for requirement in sorted(result.failed_requirements, key=lambda x: x.identifier):
            yield Align(f"\n[profile: [magenta bold]{requirement.profile.name}[/magenta bold]]", align="right")

            yield Padding(
                f"[bold][cyan][u][ {requirement.identifier} ]: "
                f"{Markdown(requirement.name).markup}[/u][/cyan][/bold]", (0, 5))
            yield Padding(Markdown(requirement.description), (1, 6))
            yield Padding("[white bold u]  Failed checks  [/white bold u]\n", (0, 8))

            for check in sorted(result.get_failed_checks_by_requirement(requirement),
                                key=lambda x: (-x.severity.value, x)):
                issue_color = get_severity_color(check.level.severity)
                yield Padding(
                    f"[bold][{issue_color}][ {check.identifier.center(16)} ][/{issue_color}] "
                    f"[magenta]{check.name}[/magenta][/bold]:",
                    (0, 7)
                )
                yield Padding(Markdown(check.description), (0, 0, 0, len(check.identifier) + 13))
                yield Padding("[u] Detected issues [/u]", (0, 8))
                for issue in sorted(result.get_issues_by_check(check),
                                    key=lambda x: (-x.severity.value, x)):
                    path = ""
                    if issue.violatingProperty and issue.violatingPropertyValue:
                        path = f" of [yellow]{issue.violatingProperty}[/yellow]"
                    if issue.violatingPropertyValue:
                        if issue.violatingProperty:
                            path += "="
                        path += f"\"[green]{issue.violatingPropertyValue}[/green]\" "  # keep the ending space
                    if issue.violatingEntity:
                        path = f"{path} on [cyan]<{issue.violatingEntity}>[/cyan]"
                    yield Padding(f"- [[red]Violation[/red]{path}]: "
                                  f"{Markdown(issue.message).markup}", (0, 9))
                    if console.no_color:
                        yield Padding("\n", (0, 0))
            yield Padding("\n", (0, 0))


class ValidationStatisticsTextOutputFormatter(OutputFormatter):

    def __init__(self, validation_statistics: ValidationStatistics):
        self._validation_statistics = validation_statistics

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        layout = ValidationReportLayout(
            console=console,
            settings=self._validation_statistics.validation_settings,
            statistics=self._validation_statistics
        )
        logger.debug(layout.layout)
        yield layout.layout
        yield Padding("\n", (0, 0))
