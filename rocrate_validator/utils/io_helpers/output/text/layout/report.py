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

import threading
import time
from typing import Callable

from requests_cache import Optional
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.colors import get_severity_color
from rocrate_validator.events import Event, EventType
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.models import (Severity, ValidationContext,
                                      ValidationResult, ValidationSettings,
                                      ValidationStatistics)
from rocrate_validator.utils.uri import URI
from rocrate_validator.utils.versioning import get_version

from .progress import ProgressMonitor

# set up logging
logger = logging.getLogger(__name__)


class ValidationReportLayout(Layout):

    def __init__(self, console: Console,
                 settings: ValidationSettings,
                 statistics: Optional[ValidationStatistics] = None,
                 profile_autodetected: bool = False):
        super().__init__()
        self.console = console
        self.validation_settings = settings
        self.statistics = statistics
        self.profile_autodetected = profile_autodetected
        self.result = None
        self.__layout = None
        self._validation_checks_progress = None
        self.__progress_monitor = None
        self.requirement_checks_container_layout = None
        self.passed_checks = None
        self.failed_checks = None
        self.report_details_container = None
        self.overall_result = None

    @property
    def layout(self):
        if not self.__layout:
            self.__init_layout__()
        return self.__layout

    @property
    def validation_checks_progress(self):
        return self._validation_checks_progress

    @property
    def progress_monitor(self) -> ProgressMonitor:
        if not self.__progress_monitor:
            self.__progress_monitor = ProgressMonitor(self.validation_settings, self.statistics)
        return self.__progress_monitor

    def live(self, update_callable: callable) -> any:
        assert update_callable, "Update callable must be provided"
        # Start live rendering
        result = None
        with Live(self.layout, console=self.console, refresh_per_second=10, transient=False):
            result = update_callable()
        return result

    def __init_layout__(self):

        # Get the validation settings
        settings = self.validation_settings

        # Set the console height
        self.console.height = 31

        # Create the layout of the base info of the validation report
        severity_color = get_severity_color(settings.requirement_severity)
        base_info_layout = Layout(
            Align(
                f"\n[bold cyan]RO-Crate:[/bold cyan] [bold]{URI(settings.rocrate_uri).uri}[/bold]"
                "\n[bold cyan]Target Profile:[/bold cyan][bold magenta] "
                f"{settings.profile_identifier}[/bold magenta] "
                f"{'[italic](autodetected)[/italic]' if self.profile_autodetected else ''}"
                f"\n[bold cyan]Validation Severity:[/bold cyan] "
                f"[bold {severity_color}]{settings.requirement_severity}[/bold {severity_color}]",
                style="white", align="left"),
            name="Base Info", size=5)
        #
        self.passed_checks = Layout(name="PASSED")
        self.failed_checks = Layout(name="FAILED")
        # Create the layout of the requirement checks section
        validated_checks_container = Layout(name="Requirement Checks Validated")
        validated_checks_container.split_row(
            self.passed_checks,
            self.failed_checks
        )

        # Create the layout of the requirement checks section
        self.requirement_checks_by_severity_container_layout = Layout(name="Requirement Checks Validation", size=5)
        self.requirement_checks_by_severity_container_layout.split_row(
            Layout(name="required"),
            Layout(name="recommended"),
            Layout(name="optional")
        )

        # Create the layout of the requirement checks section
        requirement_checks_container_layout = Layout(name="Requirement Checks")
        requirement_checks_container_layout.split_column(
            self.requirement_checks_by_severity_container_layout,
            validated_checks_container
        )

        # Create the layout of the validation checks progress
        self._validation_checks_progress = Layout(
            Panel(Align(self.progress_monitor.progress, align="center"),
                  border_style="white", padding=(0, 1), title="Overall Progress"),
            name="Validation Progress", size=5)

        # Create the layout of the report container
        report_container_layout = Layout(name="Report Container Layout")
        report_container_layout.split_column(
            base_info_layout,
            Layout(Panel(requirement_checks_container_layout,
                   title="[bold]Requirements Checks Validation[/bold]", border_style="white", padding=(1, 1))),
            self._validation_checks_progress
        )

        # Create the main layout
        self.checks_stats_layout = Layout(
            Panel(report_container_layout, title="[bold]- Validation Report -[/bold]",
                  border_style="cyan", title_align="center", padding=(1, 2)))

        # Create the overall result layout
        self.overall_result = Layout(
            Padding(Rule("\n[italic][cyan]Validating ROCrate...[/cyan][/italic]"), (1, 1)), size=3)

        group_layout = Layout()
        group_layout.add_split(self.checks_stats_layout)
        group_layout.add_split(self.overall_result)

        self.__layout = Padding(group_layout, (1, 1))

        # Update the layout with the profile stats
        self.update_stats(
            self.statistics or ValidationStatistics(self.validation_settings)
        )

        # Extract the result if available
        result = self.result or (self.statistics.validation_result) if self.statistics else None
        # Show the overall result if available
        if result:
            self.__show_overall_result__(result)

    def update(self, event: Event, ctx: Optional[ValidationContext] = None):
        logger.debug("Event: %s", event.event_type)
        if event.event_type == EventType.PROFILE_VALIDATION_START:
            logger.debug("Profile validation start: %s", event.profile.identifier)
        elif event.event_type == EventType.REQUIREMENT_VALIDATION_START:
            logger.debug("Requirement validation start")
        elif event.event_type == EventType.REQUIREMENT_CHECK_VALIDATION_START:
            logger.debug("Requirement check validation start")
        elif event.event_type == EventType.REQUIREMENT_CHECK_VALIDATION_END:
            target_profile = ctx.target_validation_profile
            if not event.requirement_check.requirement.hidden and \
                    (not event.requirement_check.overridden
                     or target_profile.identifier == event.requirement_check.requirement.profile.identifier):
                if event.validation_result is not None:
                    self.update_stats(ctx.result.statistics)
            else:
                logger.debug("Skipping requirement check validation: %s", event.requirement_check.identifier)
        elif event.event_type == EventType.REQUIREMENT_VALIDATION_END:
            if not event.requirement.hidden:
                self.update_stats(ctx.result.statistics)
        # elif event.event_type == EventType.PROFILE_VALIDATION_END:
        #     pass
        elif event.event_type == EventType.VALIDATION_END:
            self.__show_overall_result__(event.validation_result)
            logger.debug("Validation ended with result: %s", event.validation_result)

    def update_stats(self, profile_stats: ValidationStatistics = None):
        assert profile_stats, "Profile stats must be provided"
        # self.profile_stats = profile_stats
        self.requirement_checks_by_severity_container_layout["required"].update(
            Panel(
                Align(
                    # str(profile_stats['check_count_by_severity'][Severity.REQUIRED]) if profile_stats else "0",
                    str(profile_stats.check_count_by_severity[Severity.REQUIRED]) if profile_stats else "0",
                    align="center"
                ),
                padding=(1, 1),
                title="Severity: REQUIRED",
                title_align="center",
                border_style="RED"
            )
        )
        self.requirement_checks_by_severity_container_layout["recommended"].update(
            Panel(
                Align(
                    str(profile_stats.check_count_by_severity[Severity.RECOMMENDED]) if profile_stats else "0",
                    align="center"
                ),
                padding=(1, 1),
                title="Severity: RECOMMENDED",
                title_align="center",
                border_style="orange1"
            )
        )
        self.requirement_checks_by_severity_container_layout["optional"].update(
            Panel(
                Align(
                    str(profile_stats.check_count_by_severity[Severity.OPTIONAL]) if profile_stats else "0",
                    align="center"
                ),
                padding=(1, 1),
                title="Severity: OPTIONAL",
                title_align="center",
                border_style="yellow"
            )
        )

        self.passed_checks.update(
            Panel(
                Align(
                    str(len(profile_stats.passed_checks)),
                    align="center"
                ),
                padding=(1, 1),
                title="PASSED Checks",
                title_align="center",
                border_style="green"
            )
        )

        self.failed_checks.update(
            Panel(
                Align(
                    str(len(profile_stats.failed_checks)),
                    align="center"
                ),
                padding=(1, 1),
                title="FAILED Checks",
                title_align="center",
                border_style="red"
            )
        )

    def __show_overall_result__(self, result: ValidationResult):
        assert result, "Validation result must be provided"
        self.result = result
        if result.passed():
            icon = "[OK]" if not self.console.interactive else "✅"
            self.overall_result.update(
                Padding(Rule(f"[bold]{icon} RO-Crate is a [green]valid[/green] "
                             f"[magenta]{result.context.target_profile.identifier}[/magenta] !!![/bold]\n\n",
                             style="bold green"), (1, 1)))
        else:
            icon = "[FAILED]" if not self.console.interactive else "❌"
            self.overall_result.update(
                Padding(Rule(f"[bold]{icon} RO-Crate is [red]not[/red] a [red]valid[/red] "
                             f"[magenta]{result.context.target_profile.identifier}[/magenta] !!![/bold]\n",
                             style="bold red"), (1, 1)))


def get_app_header_rule() -> Text:
    return Padding(Rule(f"\n[bold][cyan]ROCrate Validator[/cyan] (ver. [magenta]{get_version()}[/magenta])[/bold]",
                        style="bold cyan"), (1, 2))


class LiveReportLayout(ValidationReportLayout):
    """Context manager for live validation report rendering."""

    def __init__(self, console: Console, validation_settings: dict,
                 result: ValidationResult, profile_autodetected: bool = False,
                 refresh_per_second: int = 10, transient: bool = False):
        """
        Initialize the live report layout context manager.

        Args:
            console: The console to render to
            validation_settings: Dictionary of validation settings
            result: The validation result
            profile_autodetected: Whether the profile was autodetected
            refresh_per_second: Number of refreshes per second
            transient: Whether the display is transient
        """
        super().__init__(console, validation_settings, result, profile_autodetected)
        self.refresh_per_second = refresh_per_second
        self.transient = transient
        self._live = None

    def __enter__(self):
        """Enter the context and start live rendering."""
        self._live = Live(
            self,
            console=self.console,
            refresh_per_second=self.refresh_per_second,
            transient=self.transient
        )
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and stop live rendering."""
        if self._live:
            self._live.__exit__(exc_type, exc_val, exc_tb)
        return False


class LiveTextProgressLayout:
    """Context manager for live validation report rendering with text progress."""

    def __init__(self, console: Console,
                 profile_identifier: str,
                 validation_settings: dict,
                 callable_service: Callable,
                 refresh_per_second: int = 10, transient: bool = False):
        """
        Initialize the live text progress layout context manager.
        Args:
            console: The console to render to
            validation_settings: Dictionary of validation settings
            refresh_per_second: Number of refreshes per second
            transient: Whether the display is transient
        """
        self.console = console
        self.profile_identifier = profile_identifier
        self.callable_service = callable_service
        self.validation_settings = validation_settings
        self.refresh_per_second = refresh_per_second
        self.transient = transient
        self._live = None

    def __enter__(self):

        # Create initial message
        message = Text()
        message.append(f"\n{' '*2}🔍 ", style="")
        message.append("Validating RO-Crate against profile: ", style="bold")
        message.append(f"{self.profile_identifier}", style="cyan")
        message.append("... ", style="bold")

        with Live(message, console=self.console, refresh_per_second=4) as live:
            # Start validation in background while updating dots

            result_container = [None]
            exception_container = [None]

            def run_validation():
                try:
                    result_container[0] = self.callable_service(self.validation_settings)
                except Exception as e:
                    exception_container[0] = e

            validation_thread = threading.Thread(target=run_validation)
            validation_thread.start()

            # Animate dots while validation runs
            dot_count = 0
            while validation_thread.is_alive():
                dot_count += 1
                message = Text()
                message.append(f"\n{' '*2}🔍 ", style="")
                message.append("Validating RO-Crate against profile: ", style="bold")
                message.append(f"{self.profile_identifier}", style="cyan")
                message.append("." * dot_count, style="bold")
                live.update(message)
                time.sleep(0.25)
            # Wait for the validation thread to finish
            validation_thread.join()
            # Check for exceptions
            if exception_container[0]:
                raise exception_container[0]
            message.append(" DONE!", style="bold")
            # Final update to indicate completion
            return result_container[0]

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and stop live rendering."""
        return False
