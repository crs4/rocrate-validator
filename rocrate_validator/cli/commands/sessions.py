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

"""
``rocrate-validator sessions`` subcommand: inspect and clear the auto-managed
batch validation sessions stored under the user cache directory.
"""

from __future__ import annotations

import copy as _copy
import json
import os
from datetime import datetime
from pathlib import Path

from rich.table import Table

from rocrate_validator import services
from rocrate_validator.cli.commands.errors import handle_error
from rocrate_validator.cli.main import cli, click
from rocrate_validator.cli.ui.text.validate import (
    BatchValidationCommandView,
    format_profile_selection,
    render_batch_footer,
    render_batch_header,
)
from rocrate_validator.constants import BYTES_PER_KIB
from rocrate_validator.models import BatchSession, BatchValidationResult, ValidationSettings
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.input import single_choice
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.utils.io_helpers.output.text.statistics import (
    render_statistics,
    render_statistics_md,
)
from rocrate_validator.utils.paths import get_user_sessions_dir

logger = logging.getLogger(__name__)

# Session states whose validation has not finished and can therefore be resumed.
_RESUMABLE_STATUSES = ("in_progress", "interrupted")


@cli.group("sessions")
@click.pass_context
def sessions(ctx):  # pylint: disable=unused-argument
    """
    [magenta]rocrate-validator:[/magenta] Manage auto-managed batch validation sessions
    """


@sessions.command("path")
@click.pass_context
def sessions_path(ctx):
    """
    Print the directory where batch sessions are stored.
    """
    console = ctx.obj["console"]
    console.print(str(get_user_sessions_dir()))


@sessions.command("show")
@click.argument("session_id", required=False)
@click.option(
    "--stats",
    "--statistics",
    "stats",
    is_flag=True,
    default=False,
    help="Append textual statistics about the session",
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write statistics to a file instead of the console (requires --stats)",
)
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["text", "md"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Output format when writing to a file (text or markdown)",
)
@click.option(
    "--color/--no-color",
    "color",
    is_flag=True,
    default=None,
    help="Keep ANSI colour codes in the file output (text format only)",
)
@click.pass_context
def sessions_show(
    ctx,
    session_id: str | None = None,
    stats: bool = False,
    output_file: Path | None = None,
    output_format: str = "text",
    color: bool | None = None,
):
    """
    Show the recorded output of a stored batch session.

    Pass a session ID (the short ID shown by `sessions list` is enough), or run
    without arguments in interactive mode to pick one from a menu. The session
    header and the summary table are rendered from what was saved, without
    re-validating anything; add --stats for the textual statistics.

    Use --output-file to write the statistics to a file instead of the console.
    Supported formats are ``text`` (plain or ANSI-coloured) and ``md`` (markdown).
    """
    console = ctx.obj["console"]
    interactive = ctx.obj.get("interactive", False)
    if not session_id and not interactive:
        raise click.UsageError("Specify a session ID (run `sessions list` to see the available sessions).")
    if output_file and not stats:
        raise click.UsageError("--output-file requires --stats.")
    try:
        summaries = _collect_sessions()
        target = _select_session(console, summaries, session_id)
        if target is None:
            return
        _show_session(
            console,
            Path(target["file"]),
            stats=stats,
            output_file=output_file,
            output_format=output_format,
            color=color,
        )
    except Exception as e:
        handle_error(e, console)


def _select_session(console, summaries: list[dict], session_id: str | None) -> dict | None:
    """
    Resolve which session to act on (any status). With an explicit ``session_id``
    the session is matched by ID prefix; without one the stored sessions are
    offered as an interactive menu. Returns the chosen summary, or ``None``.
    """
    if session_id:
        matches = [s for s in summaries if s["id"].startswith(session_id)]
        if not matches:
            console.print(f"[yellow]No session matches ID:[/yellow] {session_id}")
            return None
        if len(matches) > 1:
            console.print(f"[yellow]Ambiguous ID '{session_id}' matches {len(matches)} sessions; use a longer ID.[/yellow]")
            return None
        return matches[0]
    if not summaries:
        console.print("[yellow]No batch sessions stored.[/yellow]")
        return None
    choices = [(s["id"], _resume_choice_label(s)) for s in summaries]
    chosen_id = single_choice(console, "Select a session to show:", choices)
    if not chosen_id:
        return None
    return next((s for s in summaries if s["id"] == chosen_id), None)


def _show_session(
    console,
    session_file: Path,
    *,
    stats: bool = False,
    output_file: Path | None = None,
    output_format: str = "text",
    color: bool | None = None,
) -> None:
    """Render the header and summary table of a stored session (optionally stats)."""
    session = BatchSession.load(session_file)
    entries = session.crates
    base = _common_base([e.path for e in entries])

    # Header: counts + status badge, then session/input/profiles bullet list.
    profiles, profiles_style = format_profile_selection(session.profile_identifiers, session.no_auto_profile)
    rows: list[tuple[str, str, str]] = [("Session", str(session_file), "cyan")]
    if base:
        rows.append(("Input", base, "cyan"))
    rows.append(("Profiles", profiles, profiles_style))
    render_batch_header(
        console,
        headline=f"[bold]Session[/bold] [dim]·[/dim] [cyan]{len(entries)}[/cyan] RO-Crate(s)",
        rows=rows,
        status=session.status,
    )

    # Summary table + final verdict (or interruption note). The per-crate list
    # shown live during `validate` is intentionally not reproduced here — the
    # summary table already lists every crate.
    result = BatchValidationResult(session, [])
    BatchValidationCommandView(console=console).show_summary(result, verbose=False)

    crate_dicts = [e.to_dict() for e in entries]
    if stats:
        if output_file:
            _write_stats_to_file(
                crate_dicts,
                output_file=output_file,
                output_format=output_format,
                color=color,
            )
            console.print(f"[dim]Statistics written to[/dim] {output_file}")
        else:
            render_statistics(console, crate_dicts)

    if session.is_completed():
        render_batch_footer(console, result, [])
    else:
        pending = sum(1 for e in entries if e.status not in ("completed", "failed"))
        console.print(
            f"\n  [yellow]⚠ Session interrupted[/yellow] — "
            f"{session.completed_crates}/{len(entries)} validated, {pending} pending\n"
        )


def _write_stats_to_file(
    crate_dicts: list[dict],
    *,
    output_file: Path,
    output_format: str,
    color: bool | None = None,
) -> None:
    """Write batch statistics to a file in the requested format."""
    if output_format == "md":
        with output_file.open("w", encoding="utf-8") as f:
            render_statistics_md(f, crate_dicts)
    else:
        with output_file.open("w", encoding="utf-8") as f:
            no_color = not color if color is not None else True
            kwargs: dict = {"file": f}
            if no_color:
                kwargs["color_system"] = None
            else:
                kwargs["color_system"] = "standard"
            out = Console(**kwargs)
            render_statistics(out, crate_dicts)


@sessions.command("resume")
@click.argument("session_id", required=False)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show the details of failed crates after resuming",
)
@click.pass_context
def sessions_resume(ctx, session_id: str | None = None, verbose: bool = False):
    """
    Resume an interrupted batch validation session.

    Pass a session ID (the short ID shown by `sessions list` is enough) to resume
    that session, or run without arguments in interactive mode to pick one from a
    menu of the still-open sessions. Validation continues from where it stopped.
    """
    console = ctx.obj["console"]
    interactive = ctx.obj.get("interactive", False)
    # Without an ID there is nothing to pick from in non-interactive mode: raise
    # the usage error before the try/except so Click reports it natively.
    if not session_id and not interactive:
        raise click.UsageError("Specify a session ID (run `sessions list` to see the available sessions).")

    exit_code = 0
    try:
        summaries = _collect_sessions()
        target = _select_resume_target(console, summaries, session_id)
        if target is None:
            return
        result = _resume_session(console, Path(target["file"]), verbose=verbose, interactive=interactive)
        exit_code = 0 if result.passed() else 1
    except Exception as e:
        handle_error(e, console)
        return
    if exit_code:
        ctx.exit(exit_code)


@sessions.command("list")
@click.option(
    "--status",
    "status_filter",
    type=click.Choice(["in_progress", "interrupted", "completed"], case_sensitive=False),
    default=None,
    show_default=False,
    help="Show only sessions in the given state",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print sessions as JSON",
)
@click.pass_context
def sessions_list(ctx, status_filter: str | None = None, as_json: bool = False):
    """
    List the stored batch validation sessions (alias: `ls`).
    """
    console = ctx.obj["console"]
    try:
        summaries = _collect_sessions(status_filter=status_filter.lower() if status_filter else None)

        if as_json:
            click.echo(json.dumps([_summary_to_dict(s) for s in summaries], indent=2))
            return

        if not summaries:
            if status_filter:
                console.print(f"[yellow]No sessions with status:[/yellow] {status_filter}")
            else:
                console.print("[yellow]No batch sessions stored.[/yellow]")
            return

        table = Table(title=f"Batch sessions ({len(summaries)})", show_lines=False)
        table.add_column("ID", no_wrap=True)
        table.add_column("Status")
        table.add_column("Crates", justify="right")
        table.add_column("Target", overflow="fold")
        table.add_column("Size", justify="right")
        table.add_column("Updated")
        for s in summaries:
            table.add_row(
                s["id"][:12],
                _format_status(s["status"]),
                _format_crates(s),
                s["target"] or "—",
                _format_bytes(s["size_bytes"]),
                _format_dt(s["updated_at"]),
            )
        console.print(table)
        console.print("[dim]Use the (short) ID with `sessions clear <ID>` to remove a specific session.[/dim]")
    except Exception as e:
        handle_error(e, console)


@sessions.command("clear")
@click.argument("ids", nargs=-1)
@click.option(
    "--all",
    "clear_all",
    is_flag=True,
    default=False,
    help="Remove every stored session",
)
@click.option(
    "--completed",
    "completed_only",
    is_flag=True,
    default=False,
    help="Remove only sessions whose validation has completed",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Do not prompt for confirmation before removing sessions",
)
@click.pass_context
def sessions_clear(
    ctx,
    ids: tuple[str, ...] = (),
    clear_all: bool = False,
    completed_only: bool = False,
    yes: bool = False,
):
    """
    Remove stored batch sessions (alias: `rm`).

    Pass one or more session IDs (the short ID shown by `sessions list` is enough),
    or use --completed / --all to select sessions in bulk.
    """
    console = ctx.obj["console"]
    interactive = ctx.obj.get("interactive", False)
    # Raise usage errors before the try/except so Click reports them natively
    # instead of routing them through the generic "unexpected error" handler.
    if not ids and not clear_all and not completed_only:
        raise click.UsageError("Specify one or more session IDs, or use --completed or --all.")

    exit_code = 0
    try:
        summaries = _collect_sessions()
        targets = _select_sessions_to_clear(summaries, ids=ids, clear_all=clear_all, completed_only=completed_only)

        if not targets:
            console.print("[green]No matching sessions to remove.[/green]")
            return

        console.print(f"[bold]Sessions to remove:[/bold] [cyan]{len(targets)}[/cyan]")
        proceed = yes
        if not yes:
            if not interactive:
                console.print("[yellow]Use --yes to remove sessions in non-interactive mode.[/yellow]")
                exit_code = 1
            elif click.confirm(f"Remove {len(targets)} session(s)?", default=False):
                proceed = True
            else:
                console.print("Aborted.")

        if proceed:
            removed = 0
            for s in targets:
                try:
                    Path(s["file"]).unlink()
                    removed += 1
                except OSError as e:
                    logger.debug("Could not remove session %s: %s", s["file"], e)
                    console.print(f"[red]Failed to remove {s['id'][:12]}: {e}[/red]")
            console.print(f"[green]Removed {removed} session(s).[/green]")
    except Exception as e:
        handle_error(e, console)
        return
    if exit_code:
        ctx.exit(exit_code)


def _select_sessions_to_clear(
    summaries: list[dict],
    *,
    ids: tuple[str, ...],
    clear_all: bool,
    completed_only: bool,
) -> list[dict]:
    """Resolve the set of sessions to remove from the requested selection criteria."""
    if clear_all:
        return list(summaries)
    selected: list[dict] = []
    if completed_only:
        selected.extend(s for s in summaries if s["status"] == "completed")
    if ids:
        for requested in ids:
            matches = [s for s in summaries if s["id"].startswith(requested)]
            if not matches:
                logger.debug("No session matches ID prefix '%s'", requested)
            selected.extend(matches)
    # De-duplicate while preserving order (a session may match both filters).
    seen: set[str] = set()
    unique: list[dict] = []
    for s in selected:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    return unique


def _select_resume_target(
    console,
    summaries: list[dict],
    session_id: str | None,
) -> dict | None:
    """
    Resolve which session to resume.

    With an explicit ``session_id`` the session is matched by ID prefix (and must
    still be resumable). Without one the open sessions are offered as an
    interactive menu (the caller guarantees interactive mode in that case).
    Returns the chosen summary, or ``None`` when there is nothing to resume
    (a message is printed in that case).
    """
    if session_id:
        matches = [s for s in summaries if s["id"].startswith(session_id)]
        if not matches:
            console.print(f"[yellow]No session matches ID:[/yellow] {session_id}")
            return None
        if len(matches) > 1:
            console.print(f"[yellow]Ambiguous ID '{session_id}' matches {len(matches)} sessions; use a longer ID.[/yellow]")
            return None
        target = matches[0]
        if target["status"] not in _RESUMABLE_STATUSES:
            console.print(
                f"[green]Session {target['id'][:12]} is already '{target['status']}'; nothing to resume.[/green]"
            )
            return None
        return target

    resumable = [s for s in summaries if s["status"] in _RESUMABLE_STATUSES]
    if not resumable:
        console.print("[yellow]No resumable (interrupted) sessions found.[/yellow]")
        return None
    choices = [(s["id"], _resume_choice_label(s)) for s in resumable]
    chosen_id = single_choice(console, "Select a session to resume:", choices)
    if not chosen_id:
        return None
    return next((s for s in resumable if s["id"] == chosen_id), None)


def _resume_choice_label(summary: dict) -> str:
    """Build the menu label for a resumable session."""
    total = summary["total_crates"]
    completed = summary["completed_crates"] or 0
    progress = f"{completed}/{total}" if total is not None else "?"
    target = summary["target"] or "—"
    return f"{summary['id'][:12]}  [{summary['status']}]  {progress}  {target}"


def _resume_session(console, session_file: Path, *, verbose: bool, interactive: bool):
    """Reconstruct the settings from a saved session and continue its validation."""
    session = BatchSession.load(session_file)
    crate_paths = [c.path for c in session.crates]

    # Rebuild the validation settings stored with the session, re-injecting the
    # one outcome-affecting field dropped by ValidationSettings.to_dict().
    settings_dict = dict(session.validation_settings)
    settings_dict.setdefault("rocrate_uri", ".")
    settings_dict["requirement_severity_only"] = session.requirement_severity_only
    settings = ValidationSettings.parse(settings_dict)

    # The session does not store the original scan root, so derive a base from the
    # crate paths to show them relative (and report it as the input below).
    base = _common_base(crate_paths)

    pending = sum(1 for c in session.crates if c.status != "completed")
    if interactive:
        # Header up front: session, input and profiles, before the per-crate list,
        # so the relative crate paths shown during validation are easy to interpret.
        profiles, profiles_style = format_profile_selection(session.profile_identifiers, session.no_auto_profile)
        header_rows: list[tuple[str, str, str]] = [("Session", str(session_file), "cyan")]
        if base:
            header_rows.append(("Input", base, "cyan"))
        header_rows.append(("Profiles", profiles, profiles_style))
        render_batch_header(
            console,
            headline=(
                f"[bold]Resuming session[/bold] [dim]·[/dim] "
                f"[cyan]{pending}[/cyan] of [cyan]{len(crate_paths)}[/cyan] crate(s) to validate"
            ),
            rows=header_rows,
            status=session.status,
        )

    view = BatchValidationCommandView(console=console)
    result = view.run_with_progress(
        batch_validate_fn=services.batch_validate,
        settings=settings,
        rocrate_uris=crate_paths,
        session_path=session_file,
        fresh=False,
        profile_identifiers=session.profile_identifiers,
        no_auto_profile=session.no_auto_profile,
        base_path=Path(base) if base else None,
    )
    view.show_summary(result, verbose=verbose)

    # Aligned footer, consistent with `validate`: the session is only repeated
    # here when the run did not finish (the input is shown in the header above).
    rows: list[tuple[str, str, str, str]] = []
    if not result.session.is_completed():
        rows.append(("💾", "Session", str(session_file), "cyan"))
    render_batch_footer(console, result, rows)
    return result


def _common_base(crate_paths: list[str]) -> str | None:
    """Return a base directory for the crate paths, used for relative display."""
    paths = [p for p in crate_paths if p]
    if not paths:
        return None
    if len(paths) == 1:
        # A single crate: its parent is the natural base (shows the crate by name).
        return str(Path(paths[0]).parent)
    try:
        return os.path.commonpath(paths)
    except (ValueError, TypeError):
        return None


def _collect_sessions(status_filter: str | None = None) -> list[dict]:
    """
    Read every stored session file and return a list of summary dicts, most
    recently updated first. Filtering happens here so the table and JSON
    rendering paths share the same data shape.
    """
    sessions_dir = get_user_sessions_dir()
    if not sessions_dir.is_dir():
        return []
    summaries: list[dict] = []
    for path in sessions_dir.glob("*.json"):
        summary = _read_session_summary(path)
        if status_filter and summary["status"] != status_filter:
            continue
        summaries.append(summary)
    summaries.sort(
        key=lambda s: s["updated_at"] or datetime.min,
        reverse=True,
    )
    return summaries


def _read_session_summary(path: Path) -> dict:
    """
    Build a summary dict for a single session file. Falls back to a minimal
    summary (status ``unknown``) when the file cannot be parsed.
    """
    stat = path.stat()
    summary = {
        "id": path.stem,
        "file": str(path),
        "status": "unknown",
        "total_crates": None,
        "completed_crates": None,
        "failed_crates": None,
        "created_at": None,
        "updated_at": datetime.fromtimestamp(stat.st_mtime),
        "target": None,
        "size_bytes": stat.st_size,
    }
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        session = data.get("session", {})
        summary["status"] = session.get("status", "unknown")
        summary["total_crates"] = session.get("total_crates")
        summary["completed_crates"] = session.get("completed_crates")
        summary["failed_crates"] = session.get("failed_crates")
        summary["created_at"] = _parse_iso(session.get("created_at"))
        summary["updated_at"] = _parse_iso(session.get("updated_at")) or summary["updated_at"]
        summary["target"] = _derive_target([c.get("path", "") for c in data.get("crates", [])])
    except Exception as e:
        logger.debug("Could not parse session file %s: %s", path, e)
    return summary


def _derive_target(crate_paths: list[str]) -> str | None:
    """Return the common parent directory of the crate paths, when derivable."""
    paths = [p for p in crate_paths if p]
    if not paths:
        return None
    try:
        return os.path.commonpath(paths)
    except (ValueError, TypeError):
        return None


def _summary_to_dict(summary: dict) -> dict:
    """JSON-safe view of a session summary."""

    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    return {
        "id": summary["id"],
        "status": summary["status"],
        "total_crates": summary["total_crates"],
        "completed_crates": summary["completed_crates"],
        "failed_crates": summary["failed_crates"],
        "target": summary["target"],
        "size_bytes": summary["size_bytes"],
        "created_at": _iso(summary["created_at"]),
        "updated_at": _iso(summary["updated_at"]),
        "file": summary["file"],
    }


def _format_crates(summary: dict) -> str:
    """Render the completed/total (and failed) crate counts for the table."""
    total = summary["total_crates"]
    completed = summary["completed_crates"]
    failed = summary["failed_crates"] or 0
    if total is None:
        return "—"
    text = f"{completed or 0}/{total}"
    if failed:
        text += f" [red]({failed}✗)[/red]"
    return text


def _format_status(status: str) -> str:
    colour = {
        "completed": "green",
        "in_progress": "yellow",
        "interrupted": "yellow",
        "unknown": "red",
    }.get(status, "white")
    return f"[{colour}]{status}[/{colour}]"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M:%SZ") if value.tzinfo else value.strftime("%Y-%m-%d %H:%M:%S")


def _format_bytes(size: int) -> str:
    if size <= 0:
        return "0 B"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    idx = 0
    value = float(size)
    while value >= BYTES_PER_KIB and idx < len(units) - 1:
        value /= BYTES_PER_KIB
        idx += 1
    return f"{value:.2f} {units[idx]}"


# Shell-style aliases mirroring the `cache` command: `sessions ls` and
# `sessions rm` run the same callbacks as `list` and `clear`. Shallow copies
# give the aliases their own (hidden) names so each command appears once.
_sessions_ls_alias = _copy.copy(sessions_list)
_sessions_ls_alias.name = "ls"
_sessions_ls_alias.hidden = True
sessions.add_command(_sessions_ls_alias)

_sessions_rm_alias = _copy.copy(sessions_clear)
_sessions_rm_alias.name = "rm"
_sessions_rm_alias.hidden = True
sessions.add_command(_sessions_rm_alias)
