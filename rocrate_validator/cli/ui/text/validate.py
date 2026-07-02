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

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Group
from rich.padding import Padding
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.table import Table

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.colors import get_severity_color
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.utils.io_helpers.output.text import TextOutputFormatter
from rocrate_validator.utils.io_helpers.output.text.layout.report import ValidationReportLayout

if TYPE_CHECKING:
    from collections.abc import Callable

    from rocrate_validator.models import (
        BatchCrateEntry,
        BatchValidationResult,
        Severity,
        ValidationResult,
        ValidationSettings,
        ValidationStatistics,
    )
    from rocrate_validator.utils.io_helpers.output.pager import SystemPager

# set up logging
logger = logging.getLogger(__name__)

# Number of bytes per unit step when formatting human-readable sizes.
_BYTES_PER_UNIT = 1024
# Minimum path components below the common prefix needed to derive a source label.
_MIN_REL_PARTS_FOR_SOURCE = 2


class _SpacedProgress(Progress):
    """
    A :class:`rich.progress.Progress` that renders a blank line above its status
    bar, separating the live ``Batch: … passed … failed`` line from the per-crate
    results printed above it. The blank is part of the (transient) live region, so
    it is cleared together with the bar when validation ends.
    """

    def get_renderable(self):
        return Group("", super().get_renderable())


def format_crate_line(
    index: int,
    total: int,
    *,
    status: str,
    name: str,
    detail: str = "",
    profiles: list[str] | None = None,
    index_width: int | None = None,
    name_width: int = 0,
) -> str:
    """
    Render a single per-crate result line, shared by the live batch run and the
    static ``sessions show`` rendering so both stay identical.

    ``status`` is one of ``passed`` / ``failed`` / ``error`` / ``pending``;
    ``detail`` is the trailing text (e.g. ``(3 issues)`` or an error message).
    The running index is right-aligned and the name left-padded so the status
    text lines up across rows.
    """
    iw = index_width if index_width is not None else len(str(total))
    idx = f"[{index:>{iw}}/{total}]"
    name_cell = f"{name:<{name_width}}"
    prof = f"  [white]profile:[/white] [bold magenta]{', '.join(profiles)}[/bold magenta]" if profiles else ""
    if status == "passed":
        return f"  [green]✓[/green] {idx} {name_cell}  [bold green]passed[/bold green] [green]{detail}[/green]{prof}"
    if status == "failed":
        return f"  [red]✗[/red] {idx} {name_cell}  [bold red]failed[/bold red] [red]{detail}[/red]{prof}"
    if status == "error":
        return f"  [yellow]⚠[/yellow] {idx} {name_cell}  [yellow]{detail}[/yellow]"
    return f"  [dim]·[/dim] {idx} {name_cell}  [dim]pending[/dim]"


_STATUS_STYLES = {
    "completed": "green",
    "in_progress": "yellow",
    "interrupted": "yellow",
    "unknown": "red",
}


def format_profile_selection(profile_identifiers: list[str] | None, no_auto_profile: bool) -> tuple[str, str]:
    """Return the profile-selection label and its Rich style for the header."""
    if profile_identifiers:
        return ", ".join(profile_identifiers), "magenta"
    if no_auto_profile:
        return "ro-crate (auto-detection disabled)", "dim italic"
    return "auto-detected per crate", "dim italic"


def render_batch_header(
    console: Console,
    *,
    headline: str,
    rows: list[tuple[str, str, str]],
    status: str | None = None,
) -> None:
    """
    Render the batch/session header: a headline (optionally with a coloured status
    badge) followed by a bullet list of ``(label, value, value_style)`` rows with
    bold labels aligned to a common width.

    Shared by the ``validate`` batch run and the ``sessions show``/``resume``
    commands so the header looks the same everywhere.
    """
    console.print()
    if status:
        st = _STATUS_STYLES.get(status, "white")
        headline = f"{headline}   [{st}]●[/{st}] [bold {st}]{status}[/bold {st}]"
    console.print(headline)
    console.print()
    label_width = max((len(label) for label, _, _ in rows), default=0)
    for label, value, value_style in rows:
        console.print(f"  [dim]•[/dim] [bold]{label:<{label_width}}[/bold]   [{value_style}]{value}[/{value_style}]")
    console.print()


def render_batch_footer(
    console: Console,
    batch_result: BatchValidationResult,
    rows: list[tuple[str, str, str, str]],
) -> None:
    """
    Render the final batch verdict followed by an aligned details block.

    Shared by the ``validate`` and ``sessions resume`` commands so their output
    stays consistent. ``rows`` is a list of ``(icon, label, path, path_style)``
    tuples; labels are padded to a common width. The whole block is indented by
    two spaces so the icons line up with the per-crate ``✓``/``✗`` marks printed
    above it.
    """
    indent = "  "
    if batch_result.passed():
        console.print(
            f"\n{indent}[green]✅ [bold]All {batch_result.total_crates()} RO-Crate(s) passed validation![/bold][/green]"
        )
    else:
        console.print(
            f"\n{indent}[red]❌ [bold]{len(batch_result.failed_entries())} "
            f"out of {batch_result.total_crates()} RO-Crate(s) failed validation.[/bold][/red]"
        )
    if rows:
        label_width = max(len(label) for _, label, _, _ in rows)
        console.print()  # blank line separating the verdict from the details block
        for icon, label, path, path_style in rows:
            console.print(f"{indent}{icon} [bold]{label:<{label_width}}[/bold]  [{path_style}]{path}[/{path_style}]")
    console.print()  # trailing blank line to separate the output from the next prompt


class ValidationCommandView:
    """
    A class to handle the validation command view
    """

    def __init__(
        self,
        validation_settings: ValidationSettings | None,
        interactive: bool = True,
        no_paging: bool = False,
        pager: SystemPager | None = None,
        console: Console | None = None,
    ):
        self.console = console or Console()
        self.interactive = interactive
        self.pager = pager if not no_paging else None
        # reference to the validation settings
        self.validation_settings = validation_settings
        # reference to the report layout
        self._report_layout: ValidationReportLayout | None = None

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
            assert self.validation_settings is not None, "Validation settings must be set"
            self._report_layout = ValidationReportLayout(console=self.console, settings=self.validation_settings)

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
            lambda: validation_command(self.validation_settings, subscribers=self.report_layout.subscribers)
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

        with self.console.pager(pager=self.pager, styles=not self.console.no_color) if self.pager else self.console:
            self.console.print(statistics)

    def display_validation_result(self, result: ValidationResult) -> None:
        """
        Display the validation report layout

        Args:
            result: The validation result
        """
        assert result is not None, "Validation result must be provided"

        logger.debug("Displaying validation result")

        with self.console.pager(pager=self.pager, styles=not self.console.no_color) if self.pager else self.console:
            self.console.print(result)


class BatchValidationCommandView:
    """
    Displays batch validation progress and results in text mode.
    """

    def __init__(self, console: Console):
        self._console = console
        self.console.register_formatter(TextOutputFormatter())

    @property
    def console(self) -> Console:
        return self._console

    def run_with_progress(
        self,
        batch_validate_fn: Callable,
        settings: ValidationSettings,
        rocrate_uris: list[str],
        session_path: Path | None = None,
        fresh: bool = False,
        profile_identifiers: list[str] | None = None,
        no_auto_profile: bool = False,
        base_path: Path | None = None,
    ) -> BatchValidationResult:
        """
        Run batch validation with a persistent Rich progress bar on stderr.

        The progress bar stays visible at the bottom of the terminal during
        validation and is replaced by the summary once complete. When ``base_path``
        is given, each crate is shown relative to it so the lines stay short.
        """
        total = len(rocrate_uris)
        passed_count = 0
        failed_count = 0

        def _display(crate_path: str) -> str:
            """Render a crate path relative to ``base_path`` (the scan root) when possible."""
            if base_path is None:
                return crate_path
            try:
                rel = os.path.relpath(crate_path, base_path)
            except ValueError:
                return crate_path
            return "." if rel == os.curdir else rel

        # Column widths so the per-crate lines line up: a fixed-width running index
        # (e.g. "[ 1/43]") and crate names padded to the longest name, so the
        # trailing "passed (N issues)" / "failed (N issues)" all start at the same
        # column.
        index_width = len(str(total))
        name_width = max((len(_display(p)) for p in rocrate_uris), default=0)

        # Use stderr for progress so it's always visible even when stdout
        # is redirected to a file.
        progress_console = Console(
            file=sys.stderr,
            no_color=getattr(self.console, "no_color", False),
            width=getattr(self.console, "width", None),
        )

        progress = _SpacedProgress(
            TextColumn("{task.description}", justify="left"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•", style="dim"),
            TimeElapsedColumn(),
            console=progress_console,
            transient=True,
            expand=True,
        )

        with progress:
            task = progress.add_task(
                description="[cyan]⏳ Initialising batch...[/cyan]",
                total=total,
            )

            def _progress_callback(crate_path, index, total, status, message, profiles=None):
                nonlocal passed_count, failed_count
                # Finalisation: writing a large session to disk can take a moment;
                # show it on the bar so the run does not look frozen at 100%.
                if status == "saving":
                    progress.update(task, description="[cyan]💾 Saving session…[/cyan]")
                    return
                disp = _display(crate_path)
                if status == "passed":
                    passed_count += 1
                    progress.update(task, advance=1)
                elif status in ("failed", "error"):
                    failed_count += 1
                    progress.update(task, advance=1)
                if status in ("passed", "failed", "error"):
                    progress_console.print(
                        format_crate_line(
                            index,
                            total,
                            status=status,
                            name=disp,
                            detail=message or "",
                            profiles=profiles,
                            index_width=index_width,
                            name_width=name_width,
                        )
                    )
                # Update the status line at the bottom
                remaining = total - passed_count - failed_count
                progress.update(
                    task,
                    description=(
                        f"[bold]Batch:[/bold] "
                        f"[green]{passed_count} passed[/green] "
                        f"[red]{failed_count} failed[/red] "
                        f"[dim]{remaining} remaining[/dim]"
                    ),
                )

            return batch_validate_fn(
                settings=settings,
                rocrate_uris=rocrate_uris,
                session_path=session_path,
                fresh=fresh,
                progress_callback=_progress_callback,
                profile_identifiers=profile_identifiers,
                no_auto_profile=no_auto_profile,
            )

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        """Format a byte count as a human-readable string."""
        size = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < _BYTES_PER_UNIT:
                return f"{size:.1f} {unit}"
            size /= _BYTES_PER_UNIT
        return f"{size:.1f} TB"

    @staticmethod
    def _crate_disk_size(crate_path: str) -> str | None:
        """Return a human-readable disk size for a crate path, or None if unavailable."""
        try:
            p = Path(crate_path)
            if p.is_dir():
                total_bytes = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            elif p.is_file():
                total_bytes = p.stat().st_size
            else:
                return None
        except OSError:
            return None
        return BatchValidationCommandView._format_size(total_bytes)

    @staticmethod
    def _summary_source_and_name(crate_path: str, common: str, common_prefix: str) -> tuple[str, str]:
        """Split a crate path into a (source, crate-name) pair relative to the common prefix."""
        if common_prefix and crate_path.startswith(common_prefix):
            rel_parts = Path(crate_path[len(common_prefix) :]).parts
            if len(rel_parts) >= _MIN_REL_PARTS_FOR_SOURCE:
                return rel_parts[0], str(Path(*rel_parts[1:]))
            # crate is a direct child of common prefix: use common's last dir as source
            return Path(common).name, (rel_parts[0] if rel_parts else crate_path)
        return Path(crate_path).parent.name, Path(crate_path).name

    def _add_summary_row(
        self,
        table: Table,
        entry: BatchCrateEntry,
        *,
        common: str,
        common_prefix: str,
    ) -> None:
        """Append a single crate's summary row to the batch table from its session entry."""
        source, crate_name = self._summary_source_and_name(entry.path, common, common_prefix)
        stats = entry.statistics or {}
        size = (
            self._format_size(entry.size_bytes)
            if entry.size_bytes is not None
            else self._crate_disk_size(entry.path) or "—"
        )
        duration = entry.duration
        table.add_row(
            source,
            crate_name,
            ", ".join(entry.profiles or []) or "—",
            size,
            "[green]✓ PASSED[/green]" if entry.passed else "[red]✗ FAILED[/red]",
            str(stats.get("total_checks", 0)),
            str(stats.get("total_passed_checks", 0)),
            str(len(entry.issues or [])),
            f"{duration:.2f}s" if duration else "—",
        )

    def show_summary(self, batch_result: BatchValidationResult, verbose: bool = False):
        """
        Show the batch validation summary table and optional per-crate details.

        The table is sourced from the persistent session entries, so it stays
        complete even when this invocation only re-validated part of a resumed
        batch. The verbose per-crate details below use the live results, which
        are available only for crates validated in the current run.
        """
        total = batch_result.total_crates()
        passed = len(batch_result.passed_entries())
        failed = len(batch_result.failed_entries())

        # Summary table
        table = Table(
            title="Batch Validation Summary",
            title_style="bold",
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
            expand=True,
        )
        table.add_column("Source", style="dim", no_wrap=True)
        table.add_column("RO-Crate", style="white", no_wrap=True, ratio=1)
        table.add_column("Profile", style="cyan", no_wrap=True)
        table.add_column("Size", justify="right", min_width=9)
        table.add_column("Status", min_width=8, max_width=10)
        table.add_column("Checks", justify="right", min_width=6)
        table.add_column("Passed", justify="right", min_width=6)
        table.add_column("Issues", justify="right", min_width=6)
        table.add_column("Duration", justify="right", min_width=8)

        # Compute common prefix once so the first path component after it
        # always identifies the repository source (workflowhub, rohub, …),
        # even for deeply-nested crates like .../workflowhub/id/subdir/crate.
        all_paths = [entry.path for entry in batch_result.crates]
        try:
            common = str(Path(os.path.commonpath(all_paths)))
            common_prefix = common + os.sep
        except (ValueError, TypeError):
            common = ""
            common_prefix = ""

        for entry in batch_result.crates:
            self._add_summary_row(
                table,
                entry,
                common=common,
                common_prefix=common_prefix,
            )

        self.console.print(Padding(Rule(style="blue"), (0, 0)))
        self.console.print(table)

        # Overall stats
        self.console.print(
            Padding(
                f"\n[bold]Total: {total} crates | [green]{passed} passed[/green] | [red]{failed} failed[/red][/bold]",
                (0, 2),
            )
        )

        # Per-crate details in verbose mode. These rely on the live, in-memory
        # results, so only crates validated in the current run are shown (e.g.
        # after resuming, previously-failed crates appear in the table above but
        # their deep details are not re-rendered).
        live_failures = [(p, r) for p, r in batch_result.results if not r.passed()]
        if verbose and live_failures:
            self.console.print(Padding(Rule(style="dim"), (1, 0)))
            self.console.print(Padding("[bold]Failed crate details:[/bold]", (0, 2)))
            for crate_path, result in live_failures:
                self._show_crate_detail(crate_path, result)
                self.console.print(Padding(Rule(style="dim"), (0, 0)))

    def _show_crate_detail(self, crate_path: str, result: ValidationResult):
        """
        Show detailed validation result for a single crate in verbose batch mode.
        """
        stats = result.statistics
        if not stats:
            return

        status = "PASSED" if result.passed() else "FAILED"
        color = "green" if result.passed() else "red"
        header = f"\n[{color}]✗ {status}[/{color}]: [bold]{crate_path}[/bold]"
        if stats.duration:
            header += f" ({stats.duration:.2f}s)"
        self.console.print(Padding(header, (1, 2)))
        self.console.print(
            Padding(
                f"Checks executed: {stats.total_checks} | "
                f"Passed: {len(stats.passed_checks)} | "
                f"Failed: {len(stats.failed_checks)}",
                (0, 4),
            )
        )

        # Group failed checks by severity
        checks_by_severity: dict[Severity, list] = {}
        for check in stats.failed_checks:
            checks_by_severity.setdefault(check.severity, []).append(check)

        for severity in sorted(checks_by_severity.keys(), key=lambda s: s.value, reverse=True):
            checks = checks_by_severity[severity]
            color = get_severity_color(severity)
            severity_name = severity.name.capitalize()
            self.console.print(
                Padding(
                    f"\n[bold {color}]╔══ {severity_name} ({len(checks)} failed) ═══[/bold {color}]",
                    (0, 4),
                )
            )
            for check in checks:
                self.console.print(
                    Padding(
                        f"  [bold]{check.identifier}[/bold] - {check.name}",
                        (0, 6),
                    )
                )
                issues = result.get_issues_by_check(check)
                for issue in issues:
                    self.console.print(
                        Padding(
                            f"    └─ [{color}]{severity_name}[/{color}] {issue.message}",
                            (0, 8),
                        )
                    )
