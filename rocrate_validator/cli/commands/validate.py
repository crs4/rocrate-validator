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

import csv
import sys
from contextlib import nullcontext
from pathlib import Path

import rich_click as click
from rich.padding import Padding
from rich.rule import Rule

from rocrate_validator import constants, services
from rocrate_validator.cli.commands.errors import handle_error
from rocrate_validator.cli.main import cli
from rocrate_validator.cli.ui.text.validate import (
    BatchValidationCommandView,
    ValidationCommandView,
    format_profile_selection,
    render_batch_footer,
    render_batch_header,
)
from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.models import (
    BatchValidationResult,
    Severity,
    ValidationResult,
    ValidationSettings,
)
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.input import get_single_char, multiple_choice
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.utils.io_helpers.output.json import JSONOutputFormatter
from rocrate_validator.utils.io_helpers.output.text import TextOutputFormatter
from rocrate_validator.utils.io_helpers.output.text.layout.report import LiveTextProgressLayout, get_app_header_rule
from rocrate_validator.utils.io_helpers.output.text.statistics import render_statistics
from rocrate_validator.utils.paths import get_profiles_path
from rocrate_validator.utils.uri import validate_rocrate_uri

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)

# Organise the (long) list of `validate` options into labelled sections in the
# `--help` output. Options not listed here are shown under a default group.
# The key is matched against the command path with fnmatch, so the leading
# wildcard makes it work regardless of the program name (entry point, `python -m`,
# or the test runner). Applied via the command's own ``rich_config`` below.
_VALIDATE_OPTION_GROUPS = {
    "* validate": [
        {
            "name": "Batch validation",
            "options": [
                "--batch",
                "--batch-pattern",
                "--no-resume",
                "--stats",
            ],
        },
        {
            "name": "Profiles",
            "options": [
                "--profile-identifier",
                "--no-auto-profile",
                "--disable-profile-inheritance",
                "--profiles-path",
                "--extra-profiles-path",
            ],
        },
        {
            "name": "Requirements & checks",
            "options": [
                "--requirement-severity",
                "--requirement-severity-only",
                "--skip-checks",
                "--metadata-only",
                "--fail-fast",
                "--relative-root-path",
                "--creation-time",
                "--enforce-availability",
                "--skip-availability-check",
            ],
        },
        {
            "name": "Output",
            "options": [
                "--output-format",
                "--output-file",
                "--output-line-width",
                "--verbose",
                "--no-paging",
            ],
        },
        {
            "name": "Cache & network",
            "options": [
                "--cache-max-age",
                "--cache-path",
                "--no-cache",
                "--offline",
            ],
        },
    ],
}


def validate_uri(ctx, param, value):  # pylint: disable=unused-argument
    """
    Validate if the value is a path or a URI

    ``ctx`` is part of the click callback signature but is not used here.
    """
    if value:
        try:
            validate_rocrate_uri(value)
        except ROCrateInvalidURIError as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Invalid RO-Crate URI provided: %s", value)
            raise click.BadParameter(e.message, param=param) from e
    return value


@cli.command("validate")
@click.rich_config(
    help_config=click.RichHelpConfiguration(
        text_markup="rich",
        option_groups=_VALIDATE_OPTION_GROUPS,  # type: ignore[arg-type]
    )
)
@click.argument("rocrate-uri", callback=validate_uri, default=".")
@click.option(
    "-rr",
    "--relative-root-path",
    help="Use root-relative paths for all file references in the RO-Crate",
    default=None,
    show_default=True,
)
@click.option(
    "-m",
    "--metadata-only",
    is_flag=True,
    help="Validate only the metadata of the RO-Crate",
    default=False,
    show_default=True,
)
@click.option("-ff", "--fail-fast", is_flag=True, help="Fail fast validation mode", default=False, show_default=True)
@click.option(
    "--creation-time",
    is_flag=True,
    help="Treat availability checks as required (creation time validation)",
    default=False,
    show_default=True,
)
@click.option(
    "--enforce-availability",
    is_flag=True,
    help="Force availability checks as required",
    default=False,
    show_default=True,
)
@click.option(
    "--skip-availability-check",
    is_flag=True,
    help="Skip availability checks for web-based data entities",
    default=False,
    show_default=True,
)
@click.option(
    "--profiles-path",
    type=click.Path(exists=True),
    default=DEFAULT_PROFILES_PATH,
    show_default=True,
    help="Path containing the profiles files",
)
@click.option(
    "--extra-profiles-path",
    type=click.Path(exists=True),
    default=None,
    show_default=True,
    help="Path containing additional user profiles files",
)
@click.option(
    "-p",
    "--profile-identifier",
    multiple=True,
    type=click.STRING,
    default=None,
    show_default=True,
    metavar="Profile-ID",
    help="Identifier of the profile to use for validation",
)
@click.option(
    "-np",
    "--no-auto-profile",
    is_flag=True,
    help="Disable automatic detection of the profile to use for validation",
    default=False,
    show_default=True,
)
@click.option(
    "-nh",
    "--disable-profile-inheritance",
    is_flag=True,
    help="Disable inheritance of profiles",
    default=False,
    show_default=True,
)
@click.option(
    "-l",
    "--requirement-severity",
    type=click.Choice([s.name for s in Severity], case_sensitive=False),
    default=Severity.REQUIRED.name,
    show_default=True,
    help="Severity of the requirements to validate",
)
@click.option(
    "-lo",
    "--requirement-severity-only",
    is_flag=True,
    help="Validate only the requirements of the specified severity (no requirements with lower severity)",
    default=False,
    show_default=True,
)
@click.option(
    "-s",
    "--skip-checks",
    multiple=True,
    type=click.STRING,
    default=None,
    show_default=True,
    metavar="Fully-Qualified-Check-IDs",
    help=(
        "[bold yellow]Fully-Qualified-Check-IDs[/bold yellow] is a comma-separated list of checks to skip "
        "(may be specified multiple times). Each check must be specified by its "
        "Fully Qualified Identifier, e.g., [bold cyan]ro-crate-1.1_12.1[/bold cyan]. The fully qualified "
        "check identifier has the format <Profile-ID>_<Requirement_#>.<RequirementCheck_#>, "
        "where <Requirement_#> is the position number of the Requirement in the profile, "
        "and <RequirementCheck_#> is the position number of the RequirementCheck within that Requirement. "
        "You can find the Fully-Qualified-Check IDs using: "
        "[bold orange1]rocrate-validator profiles describe <Profile-ID> -v[/bold orange1]"
    ),
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Output the validation details without prompting",
    default=False,
    show_default=True,
)
@click.option(
    "--no-paging",
    is_flag=True,
    help="Disable pagination of the validation details",
    default=False,
    show_default=True,
    hidden=sys.platform == "win32",
)
@click.option(
    "-f",
    "--output-format",
    type=click.Choice(["text", "csv", "json"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Output format of the validation report ([bold]csv[/bold] is available in batch mode only)",
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(path_type=Path),
    default=None,
    show_default=True,
    help="Path to the output file for the validation report",
)
@click.option(
    "-w",
    "--output-line-width",
    type=click.INT,
    default=120,
    show_default=True,
    help="Width of the output line",
)
@click.option(
    "--cache-max-age",
    type=click.INT,
    default=constants.DEFAULT_HTTP_CACHE_MAX_AGE,
    show_default=True,
    help="Maximum age of the HTTP cache in seconds ([bold green]-1[/bold green] for no expiration)",
)
@click.option(
    "--cache-path",
    type=click.Path(),
    default=None,
    show_default=True,
    help="Path to the HTTP cache directory",
)
@click.option(
    "-nc",
    "--no-cache",
    is_flag=True,
    help=(
        "Disable the HTTP cache entirely: every request goes to the network "
        "and nothing is persisted. Incompatible with [bold]--offline[/bold]."
    ),
    default=False,
    show_default=True,
)
@click.option(
    "--offline",
    is_flag=True,
    help=(
        "Offline mode: HTTP requests are served only from the cache. "
        "Pre-populate the cache with [bold]rocrate-validator cache warm[/bold]."
    ),
    default=False,
    show_default=True,
)
# Batch mode options
@click.option(
    "-b",
    "--batch",
    is_flag=True,
    help="Validate every RO-Crate found under the [bold]RO-CRATE-URI[/bold] directory",
    default=False,
    show_default=True,
)
@click.option(
    "--batch-pattern",
    type=click.STRING,
    default="*",
    show_default=True,
    help="Glob pattern to filter RO-Crates in batch mode",
)
@click.option(
    "--no-resume",
    is_flag=True,
    help=(
        "Ignore any auto-saved batch session and re-validate every RO-Crate "
        "from scratch (sessions are otherwise resumed automatically)"
    ),
    default=False,
    show_default=True,
)
@click.option(
    "--stats",
    "--statistics",
    "stats",
    is_flag=True,
    help="Append textual statistics about the batch run (text output only)",
    default=False,
    show_default=True,
)
@click.pass_context
# The CLI command surfaces every validation option as a parameter; pylint counts
# those arguments as locals, so the limit is not meaningful here.
# pylint: disable-next=too-many-locals
def validate(
    ctx,
    profiles_path: Path = DEFAULT_PROFILES_PATH,
    extra_profiles_path: Path | None = None,
    profile_identifier: tuple[str, ...] = (),
    metadata_only: bool = False,
    creation_time: bool = False,
    enforce_availability: bool = False,
    skip_availability_check: bool = False,
    no_auto_profile: bool = False,
    disable_profile_inheritance: bool = False,
    requirement_severity: str = Severity.REQUIRED.name,
    requirement_severity_only: bool = False,
    skip_checks: list[str] | None = None,
    rocrate_uri: str | Path = ".",
    relative_root_path: Path | None = None,
    fail_fast: bool = False,
    no_paging: bool = False,
    verbose: bool = False,
    output_format: str = "text",
    output_file: Path | None = None,
    output_line_width: int | None = None,
    cache_max_age: int = constants.DEFAULT_HTTP_CACHE_MAX_AGE,
    cache_path: Path | None = None,
    no_cache: bool = False,
    offline: bool = False,
    batch: bool = False,
    batch_pattern: str = "*",
    no_resume: bool = False,
    stats: bool = False,
):
    """
    [magenta]rocrate-validator:[/magenta] Validate a RO-Crate against a profile
    """
    console: Console = ctx.obj["console"]
    pager = ctx.obj["pager"]
    interactive = ctx.obj["interactive"]
    # Get the no_paging flag
    enable_pager = not no_paging
    # override the enable_pager flag if the interactive flag is False
    if not interactive or sys.platform == "win32":
        enable_pager = False
    _log_validation_inputs(
        profiles_path=profiles_path,
        extra_profiles_path=extra_profiles_path,
        profile_identifier=profile_identifier,
        requirement_severity=requirement_severity,
        requirement_severity_only=requirement_severity_only,
        disable_profile_inheritance=disable_profile_inheritance,
        rocrate_uri=rocrate_uri,
        fail_fast=fail_fast,
        cache_max_age=cache_max_age,
        cache_path=cache_path,
        no_cache=no_cache,
        offline=offline,
    )

    # --no-cache and --offline are contradictory: offline mode requires a cache
    # to serve requests from, while no-cache disables caching entirely.
    if no_cache and offline:
        raise click.UsageError(
            "The --no-cache and --offline flags are mutually exclusive: "
            "offline mode relies on the HTTP cache to serve resources."
        )

    if rocrate_uri:
        logger.debug("rocrate_path: %s", Path(rocrate_uri).resolve())

    _warn_if_remote_offline(console, rocrate_uri, offline)

    # Batch mode is enabled by -b/--batch and scans the positional RO-CRATE-URI.
    batch_mode = batch
    _check_batch_only_options(
        batch_mode=batch_mode,
        batch_pattern=batch_pattern,
        no_resume=no_resume,
    )

    skip_checks_list = _parse_skip_checks(skip_checks)

    try:
        # Validation settings
        validation_settings = {
            "profiles_path": profiles_path,
            "extra_profiles_path": extra_profiles_path,
            "profile_identifier": profile_identifier,
            "requirement_severity": requirement_severity,
            "requirement_severity_only": requirement_severity_only,
            "disable_inherited_profiles_issue_reporting": disable_profile_inheritance,
            "rocrate_uri": rocrate_uri,
            "rocrate_relative_root_path": relative_root_path,
            "abort_on_first": fail_fast,
            "skip_checks": skip_checks_list,
            "metadata_only": metadata_only,
            "cache_max_age": cache_max_age if not no_cache else -1,
            "cache_path": cache_path,
            "offline": offline,
            "no_cache": no_cache,
            # When offline is requested, remote crate fetching must use the cache
            # instead of the "disable download" short-circuit.
            "disable_remote_crate_download": not offline,
            "creation_time": creation_time,
            "enforce_availability": enforce_availability,
            "skip_availability_check": skip_availability_check,
        }

        # Print the application header
        if output_format == "text" and output_file is None:
            console.print(get_app_header_rule())

        # Batch mode validates a directory of crates and exits with the aggregated
        # status. Profiles are resolved *per crate* inside the batch (explicit
        # selection or per-crate auto-detection), so the single-crate profile
        # resolution below is intentionally skipped for batch runs.
        if batch_mode:
            _run_batch_validation(
                console,
                base_settings=validation_settings,
                profile_identifiers=list(profile_identifier),
                no_auto_profile=no_auto_profile,
                cache_max_age=cache_max_age,
                verbose=verbose,
                rocrate_uri=rocrate_uri,
                batch_pattern=batch_pattern,
                fresh=no_resume,
                output_format=output_format,
                output_file=output_file,
                output_line_width=output_line_width,
                stats=stats,
            )

        # CSV is a batch-only report format; reject it for single-crate validation.
        if output_format == "csv":
            raise click.UsageError("The 'csv' output format is only available in batch mode (-b/--batch).")

        # Get the available profiles
        available_profiles = services.get_profiles(profiles_path, extra_profiles_path=extra_profiles_path)

        # Resolve the concrete list of profile identifiers (auto-detection,
        # interactive selection, or fallback to the base `ro-crate` profile).
        profile_identifiers, autodetection = _resolve_profile_identifiers(
            console,
            interactive,
            no_auto_profile,
            available_profiles,
            list(profile_identifier),
            validation_settings,
        )

        # Single-crate mode: validate against the selected profiles and report.
        results, is_valid = _run_single_validations(
            profile_identifiers,
            validation_settings,
            autodetection=autodetection,
            console=console,
            pager=pager,
            interactive=interactive,
            enable_pager=enable_pager,
            verbose=verbose,
            fail_fast=fail_fast,
            output_format=output_format,
            output_file=output_file,
            output_line_width=output_line_width,
        )
        if output_format == "json":
            _emit_json_report(
                results,
                profile_identifiers,
                is_valid,
                console=console,
                interactive=interactive,
                output_file=output_file,
                output_line_width=output_line_width,
            )

        # Exit with appropriate status code.
        # using ctx.exit seems to raise an Exception that gets caught below,
        # so we use sys.exit instead.
        sys.exit(0 if is_valid else 1)
    except Exception as e:
        handle_error(e, console)


# Threads the CLI options through to the batch helpers; pylint counts these
# pass-through arguments as locals, so the limit is not meaningful here.
# pylint: disable-next=too-many-locals
def _run_batch_validation(
    console: Console,
    *,
    base_settings: dict,
    profile_identifiers: list[str],
    no_auto_profile: bool,
    cache_max_age: int,
    verbose: bool,
    rocrate_uri: str | Path,
    batch_pattern: str,
    fresh: bool,
    output_format: str,
    output_file: Path | None,
    output_line_width: int | None,
    stats: bool = False,
) -> None:
    """Run batch validation end-to-end and exit with the aggregated status code."""
    crate_paths = _discover_batch_crates(
        rocrate_uri=rocrate_uri,
        batch_pattern=batch_pattern,
    )
    if not crate_paths:
        console.print("[bold yellow]No RO-Crates found for batch validation.[/bold yellow]")
        sys.exit(0)

    batch_settings = _build_batch_settings(
        base_settings,
        profile_identifiers=profile_identifiers,
        cache_max_age=cache_max_age,
        verbose=verbose,
    )
    # The batch session is auto-managed: its location is derived deterministically
    # from the scan target and settings, so re-running the same command resumes an
    # interrupted session automatically (no user-supplied session file).
    scan_root = Path(rocrate_uri).resolve()
    session_path = services.resolve_batch_session_path(
        batch_settings,
        scan_root,
        batch_pattern,
        profile_identifiers=profile_identifiers,
        no_auto_profile=no_auto_profile,
    )
    _print_batch_header(
        console,
        count=len(crate_paths),
        session_path=session_path,
        input_path=scan_root,
        profile_identifiers=profile_identifiers,
        no_auto_profile=no_auto_profile,
    )

    batch_view = BatchValidationCommandView(console=console)
    # Run batch validation with a progress bar on stderr (always visible,
    # even when the report goes to a file).
    batch_result = batch_view.run_with_progress(
        batch_validate_fn=services.batch_validate,
        settings=batch_settings,
        rocrate_uris=crate_paths,
        session_path=session_path,
        fresh=fresh,
        profile_identifiers=profile_identifiers,
        no_auto_profile=no_auto_profile,
        base_path=scan_root,
    )
    # Writing a large report to a file can take a moment; show a spinner on
    # stderr while it happens (skipped when the summary is rendered to the
    # console, which is itself the visible output).
    if output_file:
        status_console = Console(file=sys.stderr, no_color=console.no_color, width=console.width)
        report_ctx = status_console.status(f"[cyan]Writing report to {output_file}…[/cyan]")
    else:
        report_ctx = nullcontext()
    with report_ctx:
        _write_batch_report(
            batch_view,
            batch_result,
            output_format=output_format,
            output_file=output_file,
            output_line_width=output_line_width,
            verbose=verbose,
            stats=stats,
        )
    # Statistics are a human-readable view; they are not embedded in machine output.
    if stats and output_format in ("json", "csv"):
        Console(file=sys.stderr, no_color=console.no_color, width=console.width).print(
            f"[yellow]Note:[/yellow] --stats is ignored for '{output_format}' output (text mode only)."
        )
    _report_batch_status(
        console,
        batch_result,
        session_path=session_path,
        output_file=output_file,
        output_format=output_format,
    )
    sys.exit(0 if batch_result.passed() else 1)


# Threads the CLI options through to the rendering helpers; pylint counts these
# pass-through arguments as locals, so the limit is not meaningful here.
# pylint: disable-next=too-many-locals
def _run_single_validations(
    profile_identifiers: list[str],
    validation_settings: dict,
    *,
    autodetection: bool,
    console: Console,
    pager,
    interactive: bool,
    enable_pager: bool,
    verbose: bool,
    fail_fast: bool,
    output_format: str,
    output_file: Path | None,
    output_line_width: int | None,
) -> tuple[dict, bool]:
    """Validate the RO-Crate against each selected profile, returning (results, overall-validity)."""
    is_valid = True
    results = {}
    for profile in profile_identifiers:
        # Duplicate settings for each profile and set the profile identifier
        logger.info("\nValidating RO-Crate against profile: [bold cyan]%s[/bold cyan]", profile)
        profile_settings = validation_settings.copy()
        profile_settings["profile_identifier"] = profile
        logger.debug("Profile selected for validation: %s", profile)
        logger.debug("Profile autodetected: %s", autodetection)

        # Perform the validation and render the result for the chosen output target.
        if output_format == "text" and not output_file:
            result = _render_console_result(
                profile_settings,
                console=console,
                pager=pager,
                interactive=interactive,
                enable_pager=enable_pager,
                verbose=verbose,
            )
        else:
            result = _render_file_or_collected_result(
                profile,
                profile_settings,
                console=console,
                interactive=interactive,
                verbose=verbose,
                output_format=output_format,
                output_file=output_file,
                output_line_width=output_line_width,
            )
        results[profile] = result

        # Update the global validation status
        is_valid = is_valid and result.passed()

        # Interrupt the validation if the fail fast mode is enabled
        if fail_fast and not is_valid:
            break

    return results, is_valid


def _build_batch_settings(
    base_settings: dict,
    *,
    profile_identifiers: list[str],
    cache_max_age: int,
    verbose: bool,
) -> ValidationSettings:
    """Derive the shared batch ``ValidationSettings`` from the single-crate settings."""
    # Batch mode targets a directory of crates, so only the per-crate RO-Crate URI
    # is dropped (it is set per crate during validation). The creation-time and
    # availability flags are intentionally kept so they apply uniformly to every
    # crate, exactly as they would in single-crate validation.
    batch_settings_dict = {k: v for k, v in base_settings.items() if k != "rocrate_uri"}
    batch_settings_dict.update(
        {
            # Base profile for the shared settings object; the actual profile(s) used
            # for each crate are resolved per crate by the services layer (explicit
            # ``--profile-identifier`` list or per-crate auto-detection).
            "profile_identifier": profile_identifiers[0] if profile_identifiers else "ro-crate",
            "cache_max_age": cache_max_age,
            "verbose": verbose,
        }
    )
    return ValidationSettings.parse(batch_settings_dict)


def _discover_batch_crates(
    *,
    rocrate_uri: str | Path,
    batch_pattern: str,
) -> list[str]:
    """
    Resolve the list of RO-Crate paths to validate in batch mode by scanning the
    target directory. Auto-resume of an interrupted session is handled in the
    services layer by comparing this discovered list against the saved session.
    """
    scan_dir = Path(rocrate_uri).resolve()
    if not scan_dir.is_dir():
        raise click.BadParameter(f"Batch target must be a directory: {scan_dir}", param_hint="RO-CRATE-URI")
    return [str(p) for p in services.discover_ro_crates(scan_dir, pattern=batch_pattern)]


def _write_batch_report(
    batch_view: BatchValidationCommandView,
    batch_result: BatchValidationResult,
    *,
    output_format: str,
    output_file: Path | None,
    output_line_width: int | None,
    verbose: bool,
    stats: bool = False,
) -> None:
    """
    Write the batch result as JSON, CSV or a text summary, to a file or the console.

    When ``stats`` is set, the textual statistics are appended after the summary
    in text mode (console or file); they are a human-readable view and are not
    emitted for the machine-readable JSON/CSV formats.

    Where the report is saved is reported afterwards by :func:`_report_batch_status`,
    so this function does not print its own "writing to ..." notes.
    """
    if output_format == "json":
        with output_file.open("w", encoding="utf-8") if output_file else nullcontext(sys.stdout) as f:
            out = Console(color_system=None, width=output_line_width, file=f)
            out.register_formatter(JSONOutputFormatter())
            out.print(batch_result)
        return

    if output_format == "csv":
        with output_file.open("w", encoding="utf-8", newline="") if output_file else nullcontext(sys.stdout) as f:
            _write_batch_csv(batch_result, f)
        return

    crate_dicts = [entry.to_dict() for entry in batch_result.crates]
    if output_file:
        with output_file.open("w", encoding="utf-8") as f:
            out = Console(color_system=None, width=output_line_width, file=f)
            out.register_formatter(TextOutputFormatter())
            BatchValidationCommandView(console=out).show_summary(batch_result, verbose=verbose)
            if stats:
                render_statistics(out, crate_dicts)
    else:
        batch_view.show_summary(batch_result, verbose=verbose)
        if stats:
            render_statistics(batch_view.console, crate_dicts)


def _write_batch_csv(batch_result: BatchValidationResult, file) -> None:
    """Write the batch result as CSV (one row per crate) to an open text file."""
    writer = csv.writer(file)
    writer.writerow(
        [
            "source",
            "crate",
            "path",
            "profiles",
            "size_bytes",
            "status",
            "total_checks",
            "passed_checks",
            "issues",
            "duration",
            "error",
        ]
    )
    for entry in batch_result.crates:
        stats = entry.statistics or {}
        path = Path(entry.path)
        writer.writerow(
            [
                path.parent.name,
                path.name,
                entry.path,
                ";".join(entry.profiles or []),
                entry.size_bytes if entry.size_bytes is not None else "",
                "passed" if entry.passed else "failed",
                stats.get("total_checks", ""),
                stats.get("total_passed_checks", ""),
                len(entry.issues or []),
                f"{entry.duration:.3f}" if entry.duration is not None else "",
                entry.error or "",
            ]
        )


def _print_batch_header(
    console: Console,
    *,
    count: int,
    session_path: Path | None,
    input_path: Path,
    profile_identifiers: list[str],
    no_auto_profile: bool,
) -> None:
    """
    Print the batch header on stderr (always): the number of crates found, the
    session file, the input scanned and the profile selection. Shown before the
    per-crate list so the relative crate paths printed during validation are
    easy to interpret.
    """
    stderr_console = Console(file=sys.stderr, no_color=console.no_color, width=console.width)
    profiles, profiles_style = format_profile_selection(profile_identifiers, no_auto_profile)
    rows: list[tuple[str, str, str]] = []
    if session_path:
        rows.append(("Session", str(session_path), "cyan"))
    rows.append(("Input", str(input_path), "cyan"))
    rows.append(("Profiles", profiles, profiles_style))
    render_batch_header(
        stderr_console,
        headline=f"[bold]Batch validation[/bold] [dim]·[/dim] [cyan]{count}[/cyan] RO-Crate(s)",
        rows=rows,
    )


def _report_batch_status(
    console: Console,
    batch_result: BatchValidationResult,
    *,
    session_path: Path | None,
    output_file: Path | None,
    output_format: str,
) -> None:
    """
    Print the final batch verdict on stderr, followed by a spaced block listing
    where the report was saved (and the session, only when the run did not
    complete and may need to be resumed).

    Everything is written to stderr so it never pollutes machine-readable output
    (JSON/CSV) sent to stdout. The input scanned is reported up front by
    :func:`_print_batch_header`, so it is not repeated here.
    """
    stderr_console = Console(file=sys.stderr, no_color=console.no_color, width=console.width)

    rows: list[tuple[str, str, str, str]] = []  # (icon, label, path, path-style)
    if output_file:
        rows.append(("📄", f"Report ({output_format})", str(output_file), "bold cyan"))
    # The session is only useful here if the run did not finish (so it can be
    # resumed); when completed it is redundant with the header shown at the start.
    if session_path and not batch_result.session.is_completed():
        rows.append(("💾", "Session", str(session_path), "cyan"))
    render_batch_footer(stderr_console, batch_result, rows)


def _log_validation_inputs(
    *,
    profiles_path,
    extra_profiles_path,
    profile_identifier,
    requirement_severity,
    requirement_severity_only,
    disable_profile_inheritance,
    rocrate_uri,
    fail_fast,
    cache_max_age,
    cache_path,
    no_cache,
    offline,
) -> None:
    """Log the raw validation input parameters for debugging."""
    logger.debug("profiles_path: %s", Path(profiles_path).resolve())
    logger.debug("extra_profiles_path: %s", Path(extra_profiles_path).resolve() if extra_profiles_path else None)
    logger.debug("profile_identifier: %s", profile_identifier)
    logger.debug("requirement_severity: %s", requirement_severity)
    logger.debug("requirement_severity_only: %s", requirement_severity_only)
    logger.debug("disable_inheritance: %s", disable_profile_inheritance)
    logger.debug("rocrate_uri: %s", rocrate_uri)
    logger.debug("fail_fast: %s", fail_fast)
    logger.debug("no fail fast: %s", not fail_fast)
    logger.debug("cache_max_age: %s", cache_max_age)
    logger.debug("cache_path: %s", Path(cache_path).resolve() if cache_path else None)
    logger.debug("no_cache: %s", no_cache)
    logger.debug("offline: %s", offline)


def _warn_if_remote_offline(console: Console, rocrate_uri: str | Path, offline: bool) -> None:
    """Warn when a remote RO-Crate is validated in offline mode (the cached copy is used)."""
    if offline and isinstance(rocrate_uri, str) and rocrate_uri.split(":", 1)[0].lower() in ("http", "https", "ftp"):
        console.print(
            Padding(
                Rule(
                    "[bold yellow]WARNING:[/bold yellow] "
                    "[bold]The target RO-Crate is remote and offline mode is enabled.[/bold]\n"
                    "The cached version of the RO-Crate will be used if available.\n"
                    "The cached copy may be out of sync with the version currently published remotely.",
                    align="center",
                    style="bold yellow",
                ),
                (1, 2, 0, 2),
            )
        )


def _check_batch_only_options(
    *,
    batch_mode: bool,
    batch_pattern: str,
    no_resume: bool,
) -> None:
    """
    Reject batch-only options when batch mode is not enabled.

    ``--batch-pattern`` and ``--no-resume`` only make sense in batch mode; using
    them without ``-b/--batch`` is a usage error rather than a silently ignored
    no-op.
    """
    if batch_mode:
        return
    misused = []
    if batch_pattern != "*":
        misused.append("--batch-pattern")
    if no_resume:
        misused.append("--no-resume")
    if misused:
        joined = ", ".join(misused)
        verb = "is" if len(misused) == 1 else "are"
        raise click.UsageError(f"{joined} {verb} only valid in batch mode; enable it with -b/--batch.")


def _parse_skip_checks(skip_checks: list[str] | None) -> list[str]:
    """Parse the comma-separated ``--skip-checks`` option into a flat list of check IDs."""
    logger.debug("skip_checks: %s", skip_checks)
    skip_checks_list: list[str] = []
    if skip_checks:
        try:
            for s in skip_checks:
                skip_checks_list.extend(_.strip() for _ in s.split(",") if _.strip())
        except Exception as e:
            logger.error("Error parsing skip_checks: %s", e)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error parsing skip_checks")
            raise ValueError(
                f"Invalid skip_checks value: {skip_checks}. "
                "It must be a comma-separated list of Fully Qualified Check IDs."
            ) from e
    logger.debug("Skip checks: %s", skip_checks_list)
    return skip_checks_list


def _resolve_profile_identifiers(
    console: Console,
    interactive: bool,
    no_auto_profile: bool,
    available_profiles: list,
    profile_identifiers: list[str],
    validation_settings: dict,
) -> tuple[list[str], bool]:
    """
    Resolve the concrete list of profile identifiers to validate against.

    Applies auto-detection and interactive selection when no profile is given,
    and falls back to the base ``ro-crate`` profile when nothing can be resolved.
    Returns the identifiers and whether they were auto-detected.
    """
    autodetection = False
    if not profile_identifiers:
        # Auto-detect the profile to use for validation (if not disabled)
        candidate_profiles = None
        if not no_auto_profile:
            candidate_profiles = services.detect_profiles(settings=validation_settings)
            logger.debug("Candidate profiles: %s", candidate_profiles)
        else:
            logger.info("Auto-detection of the profiles to use for validation is disabled")

        # Prompt the user when interactive and no single profile could be auto-detected
        if interactive and (
            not candidate_profiles or len(candidate_profiles) == 0 or len(candidate_profiles) == len(available_profiles)
        ):
            console.print(
                Padding(
                    Rule(
                        "[bold yellow]WARNING: [/bold yellow]"
                        "[bold]Unable to automatically detect the profile to use for validation[/bold]\n",
                        align="center",
                        style="bold yellow",
                    ),
                    (2, 2, 0, 2),
                )
            )
            selected_options = multiple_choice(console, available_profiles)
            if selected_options is None or isinstance(selected_options, bool):
                selected_options = []
            profile_identifiers = [available_profiles[int(o)].identifier for o in selected_options]
            logger.debug("Profile selected: %s", selected_options)
            console.print(Padding(Rule(style="bold yellow"), (1, 2)))
        elif candidate_profiles and len(candidate_profiles) < len(available_profiles):
            logger.debug("Profile identifier autodetected: %s", candidate_profiles[0].identifier)
            autodetection = True
            profile_identifiers = [_.identifier for _ in candidate_profiles]

    # Fall back to the base profile when nothing could be resolved
    if not profile_identifiers:
        console.print(f"\n{' ' * 2}[bold yellow]WARNING: [/bold yellow]", end="")
        if no_auto_profile:
            console.print("[bold]Auto-detection of the profiles to use for validation is disabled[/bold]")
        else:
            console.print("[bold]Unable to automatically detect the profile to use for validation[/bold]")
        console.print(f"{' ' * 11}[bold]The base `ro-crate` profile will be used for validation[/bold]")
        profile_identifiers = ["ro-crate"]

    return profile_identifiers, autodetection


def _render_console_result(
    validation_settings: dict,
    *,
    console: Console,
    pager,
    interactive: bool,
    enable_pager: bool,
    verbose: bool,
) -> ValidationResult:
    """Validate and render the result to the interactive/text console (no output file)."""
    if interactive:
        command_view = ValidationCommandView(
            validation_settings=ValidationSettings.parse(validation_settings),
            console=console,
            interactive=interactive,
            no_paging=not enable_pager,
            pager=pager,
        )
        result = command_view.show_validation_progress(services.validate)
        if not result.passed():
            verbose_choice = "n"
            if interactive and not verbose:
                verbose_choice = get_single_char(
                    console,
                    choices=["y", "n"],
                    message=("[bold] > Do you want to see the validation details? ([magenta]y/n[/magenta]): [/bold]"),
                )
            if verbose_choice == "y" or verbose:
                command_view.display_validation_result(result)
        return result

    result = services.validate(validation_settings)
    console.register_formatter(TextOutputFormatter())
    console.print(result.statistics)
    if not result.passed() and verbose:
        out = Console(no_color=console.no_color, width=console.width, height=console.height)
        out.register_formatter(TextOutputFormatter())
        out.print(result)
    return result


def _render_file_or_collected_result(
    profile: str,
    validation_settings: dict,
    *,
    console: Console,
    interactive: bool,
    verbose: bool,
    output_format: str,
    output_file: Path | None,
    output_line_width: int | None,
) -> ValidationResult:
    """Validate for the file/JSON-input path, optionally writing a text report to file."""
    if interactive:
        with LiveTextProgressLayout(
            console=console,
            profile_identifier=profile,
            validation_settings=validation_settings,
            callable_service=services.validate,
            transient=True,
        ) as result:
            logger.debug("Validation result obtained")
    else:
        result = services.validate(validation_settings)

    if result is None:
        raise RuntimeError("Validation did not produce a result")

    # Output processing for text format to file
    if output_file and output_format == "text":
        if interactive:
            console.print(f"\n{' ' * 2}📝 [bold]Writing validation results to file[/bold]{'.' * 4} ", end="")
        with output_file.open("w", encoding="utf-8") if output_file else sys.stdout as f:
            out = Console(color_system=None, width=output_line_width, height=31, file=f)
            out.register_formatter(TextOutputFormatter())
            out.print(result.statistics)  # Output the statistics first
            if not result.passed() and verbose:
                out.print(result)
        if interactive:
            console.print(f"[bold green]{output_file}[/bold green]", end="\n")
    return result


def _emit_json_report(
    results: dict,
    profile_identifiers: list[str],
    is_valid: bool,
    *,
    console: Console,
    interactive: bool,
    output_file: Path | None,
    output_line_width: int | None,
) -> None:
    """Write the aggregated validation results as JSON to a file or stdout."""
    if interactive:
        if is_valid:
            console.print(
                f"\n{' ' * 2}✅ [bold]Validation [green]PASSED![/green]. "
                f"\n{' ' * 5}RO-Crate is valid according to the profile(s): "
                f"[cyan]{', '.join(profile_identifiers)}[/cyan][/bold]"
            )
        else:
            console.print(f"\n{' ' * 2}❌ [bold]Validation [red]FAILED![/red][/bold]")
        if output_file:
            console.print(
                f"\n{' ' * 2}📝 [bold]Writing validation results in JSON format "
                f'to the file "{output_file}"[/bold]{"." * 4} ',
                end="",
            )
        else:
            console.print(f"\n{' ' * 2}📋 [bold]The validation report in JSON format: [/bold]\n")

    # Generate the JSON output and write it to the specified output file or to stdout
    with output_file.open("w", encoding="utf-8") if output_file else nullcontext(sys.stdout) as f:
        out = Console(width=output_line_width, file=f)
        out.register_formatter(JSONOutputFormatter())
        # Disable word-wrap/cropping: Rich would otherwise insert literal line
        # breaks into long string values (e.g. messages, URLs), producing
        # invalid, unescaped control characters in the JSON output.
        out.print(results, soft_wrap=True)

    if interactive and output_file:
        console.print("[bold]DONE![/bold]", end="\n\n")
