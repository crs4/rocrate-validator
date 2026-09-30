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

import re
import sys
from pathlib import Path
from typing import Any

from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from rocrate_validator import services
from rocrate_validator.cli.commands.errors import handle_error
from rocrate_validator.cli.main import cli, click
from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.models import (
    EffectiveRequirementCheck,
    LevelCollection,
    Profile,
    RequirementCheckRelation,
    RequirementLevel,
    Severity,
)
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.colors import get_severity_color
from rocrate_validator.utils.io_helpers.output.text.layout.report import get_app_header_rule
from rocrate_validator.utils.paths import get_profiles_path, shorten_path

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


@cli.group("profiles")
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
@click.pass_context
def profiles(ctx, profiles_path: Path = DEFAULT_PROFILES_PATH, extra_profiles_path: Path | None = None):
    """
    [magenta]rocrate-validator:[/magenta] Manage profiles
    """
    logger.debug("Profiles path: %s", profiles_path)
    ctx.obj["profiles_path"] = profiles_path
    ctx.obj["extra_profiles_path"] = extra_profiles_path


@profiles.command("list")
@click.option(
    "--no-paging", is_flag=True, help="Disable paging", default=False, show_default=True, hidden=sys.platform == "win32"
)
@click.pass_context
def list_profiles(ctx, no_paging: bool = False):  # , profiles_path: Path = DEFAULT_PROFILES_PATH):
    """
    List available profiles
    """
    profiles_path = ctx.obj["profiles_path"]
    extra_profiles_path = ctx.obj["extra_profiles_path"]
    console = ctx.obj["console"]
    pager = ctx.obj["pager"]
    interactive = ctx.obj["interactive"]
    # Get the no_paging flag
    enable_pager = not no_paging
    # override the enable_pager flag if the interactive flag is False
    if not interactive or sys.platform == "win32":
        enable_pager = False

    try:
        # Get the profiles
        profiles = services.get_profiles(profiles_path=profiles_path, extra_profiles_path=extra_profiles_path)

        table = Table(
            show_header=True,
            title="   Available profiles",
            title_style="italic bold cyan",
            title_justify="left",
            header_style="bold cyan",
            border_style="bright_black",
            show_footer=False,
            caption_style="italic bold",
            caption="[cyan](*)[/cyan] Number of requirements checks by severity",
        )

        # Define columns
        table.add_column("Identifier", style="magenta bold", justify="center")
        table.add_column("URI", style="yellow bold", justify="center")
        table.add_column("Version", style="green bold", justify="center")
        table.add_column("Name", style="white bold", justify="center")
        table.add_column("Description", style="white italic")
        table.add_column("Based on", style="white", justify="center")
        table.add_column("Requirements Checks (*)", style="white", justify="center")

        # Define levels
        levels = (LevelCollection.REQUIRED, LevelCollection.RECOMMENDED, LevelCollection.OPTIONAL)

        # Add data to the table
        for profile in profiles:
            # Count requirements by severity
            checks_info: dict[str, dict[str, Any]] = {}
            for level in levels:
                checks_info[level.severity.name] = {"count": 0, "color": get_severity_color(level.severity)}

            requirements = [_ for _ in profile.get_requirements(severity=Severity.OPTIONAL) if not _.hidden]
            for requirement in requirements:
                for level in levels:
                    count = len(requirement.get_checks_by_level(level))
                    checks_info[level.severity.name]["count"] += count

            checks_summary = "\n".join(
                [f"[{v['color']}]{k}[/{v['color']}]: {v['count']}" for k, v in checks_info.items()]
            )

            # Add the row to the table
            profile_name = (
                "\n".join(map(str, profile.name)) if isinstance(profile.name, list) else str(profile.name or "")
            )

            table.add_row(
                profile.identifier,
                profile.uri,
                profile.version,
                profile_name,
                Markdown((profile.description or "").strip()),
                "\n".join([p.identifier for p in profile.inherited_profiles]),
                checks_summary,
            )
            table.add_row()

        # Print the table
        with console.pager(pager=pager, styles=not console.no_color) if enable_pager else console:
            console.print(get_app_header_rule())
            console.print(Padding(table, (0, 1)))

    except Exception as e:
        handle_error(e, console)


@profiles.command("check")
@click.argument("profile-identifier", type=click.STRING, default=DEFAULT_PROFILE_IDENTIFIER, required=True)
@click.option(
    "--no-paging", is_flag=True, help="Disable paging", default=False, show_default=True, hidden=sys.platform == "win32"
)
@click.pass_context
def check_profile(ctx, profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER, no_paging: bool = False):
    """Check the consistency of a profile and its inherited profiles."""
    console = ctx.obj["console"]
    pager = ctx.obj["pager"]
    interactive = ctx.obj["interactive"]
    enable_pager = not no_paging and interactive and sys.platform != "win32"
    failed = False

    try:
        profile = services.get_profile(
            profile_identifier,
            profiles_path=ctx.obj["profiles_path"],
            extra_profiles_path=ctx.obj["extra_profiles_path"],
        )
        profiles = [*profile.inherited_profiles, profile]
        results = [
            (checked_profile, result) for checked_profile in profiles for result in checked_profile.validate_checks()
        ]

        table = Table(
            title=f"   Profile checks: {profile.identifier}",
            title_style="italic bold cyan",
            title_justify="left",
            header_style="bold cyan",
            border_style="bright_black",
        )
        table.add_column("Profile", style="magenta bold")
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Message")
        table.add_column("Details")

        for checked_profile, result in results:
            status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
            failed |= not result.passed
            details = ", ".join(f"{key}={value}" for key, value in result.details.items())
            table.add_row(checked_profile.identifier, result.check_id, status, result.message, details)

        with console.pager(pager=pager, styles=not console.no_color) if enable_pager else console:
            console.print(get_app_header_rule())
            console.print(Padding(table, (0, 1)))

    except SystemExit:
        raise
    except Exception as e:
        handle_error(e, console)
    if failed:
        raise click.exceptions.Exit(1)


@profiles.command("describe")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed list of requirements (or, when a check identifier is given, show the source code of the check)",
    default=False,
    show_default=True,
)
@click.argument("profile-identifier", type=click.STRING, default=DEFAULT_PROFILE_IDENTIFIER, required=True)
@click.argument("check-identifier", type=click.STRING, required=False, default=None)
@click.option(
    "--no-paging", is_flag=True, help="Disable paging", default=False, show_default=True, hidden=sys.platform == "win32"
)
@click.pass_context
def describe_profile(
    ctx,
    *,
    profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER,
    check_identifier: str | None = None,
    profiles_path: Path = DEFAULT_PROFILES_PATH,
    extra_profiles_path: Path | None = None,
    verbose: bool = False,
    no_paging: bool = False,
):
    """
    Show a profile, or — when CHECK_IDENTIFIER is given — show a single requirement check.

    \b
    The check identifier accepts either form:
      * relative:   <requirement#>.<check#>          (e.g. "1.2")
      * full:       <profile>_<requirement#>.<check#> (e.g. "ro-crate-1.3_1.2")

    With -v on a single check, the source code of the check is shown.
    """

    # Get the console
    console = ctx.obj["console"]
    pager = ctx.obj["pager"]
    interactive = ctx.obj["interactive"]
    profiles_path = ctx.obj["profiles_path"]
    extra_profiles_path = ctx.obj["extra_profiles_path"]
    # Get the no_paging flag
    enable_pager = not no_paging
    # override the enable_pager flag if the interactive flag is False
    if not interactive or sys.platform == "win32":
        enable_pager = False

    try:
        # Get the profile
        profile = services.get_profile(
            profile_identifier, profiles_path=profiles_path, extra_profiles_path=extra_profiles_path
        )

        # Single-check view
        if check_identifier:
            effective_check = __resolve_check__(profile, check_identifier)
            with console.pager(pager=pager, styles=not console.no_color) if enable_pager else console:
                console.print(get_app_header_rule())
                __describe_check__(console, profile, effective_check, verbose=verbose)
            return

        # Set the subheader title
        subheader_title = f"[bold][cyan]Profile:[/cyan] [italic magenta]{profile.identifier}[/italic magenta][/bold]"

        # Set the subheader content
        subheader_content = f"[bold cyan]Version:[/bold cyan] [italic green]{profile.version}[/italic green]\n"
        subheader_content += f"[bold cyan]URI:[/bold cyan] [italic yellow]{profile.uri}[/italic yellow]\n\n"
        profile_name = profile.name or ""
        if isinstance(profile_name, list):
            profile_name = ", ".join(str(name).strip() for name in profile_name if str(name).strip())
        else:
            profile_name = str(profile_name).strip()
        subheader_content += f"[bold cyan]Name:[/bold cyan] [italic]{profile_name}[/italic]\n"
        subheader_content += (
            f"[bold cyan]Description:[/bold cyan] [italic]{(profile.description or '').strip()}[/italic]"
        )
        # Add path info to the subheader
        subheader_content += (
            "\n\n"
            "[bold cyan]Validation Profile Path:[/bold cyan] "
            "[italic green]"
            f"{shorten_path(profile.path) if hasattr(profile, 'path') and profile.path else 'N/A'}"
            "[/italic green]"
        )
        # Handle overridden and overriding profiles
        if profile.overrides:
            subheader_content += (
                "\n\n" + " " * 20 + " [[bold red]overrides: [/bold red][italic]"
                f"{', '.join(shorten_path(p.path) for p in profile.overrides)}[/italic]]"
            )
        if profile.overridden_by:
            subheader_content += (
                "\n\n" + " " * 20 + " [[bold red]overridden by: [/bold red][italic]"
                f"{', '.join(shorten_path(p.path) for p in profile.overridden_by)}[/italic]]"
            )

        # Build the profile table
        table = __compacted_describe_profile__(profile) if not verbose else __verbose_describe_profile__(profile)

        with console.pager(pager=pager, styles=not console.no_color) if enable_pager else console:
            console.print(get_app_header_rule())
            console.print(
                Padding(
                    Panel(
                        subheader_content,
                        title=subheader_title,
                        padding=(1, 1, 0, 1),
                        title_align="left",
                        border_style="cyan",
                    ),
                    (0, 1, 0, 1),
                )
            )
            console.print(Padding(table, (1, 1)))

    except click.ClickException:
        # Let click format usage errors natively (e.g., BadParameter from check resolution)
        raise
    except Exception as e:
        handle_error(e, console)


def __requirement_level_style__(requirement: RequirementLevel):
    """
    Format the requirement level
    """
    color = get_severity_color(requirement.severity)
    return f"{color} bold"


def __compacted_describe_profile__(profile):
    """
    Show a profile in a compact way
    """
    table_rows = []
    levels_list = set()
    requirements = [_ for _ in profile.requirements if not _.hidden]
    for requirement in requirements:
        # add the requirement to the list
        levels = (LevelCollection.REQUIRED, LevelCollection.RECOMMENDED, LevelCollection.OPTIONAL)
        levels_count = []
        for level in levels:
            count = len(requirement.get_checks_by_level(level))
            levels_count.append(count)
            if count > 0:
                color = get_severity_color(level.severity)
                level_info = f"[{color}]{level.severity.name}[/{color}]"
                levels_list.add(level_info)
        table_rows.append(
            (
                str(requirement.order_number),
                requirement.name,
                Markdown(requirement.description.strip()),
                f"{levels_count[0]}",
                f"{levels_count[1]}",
                f"{levels_count[2]}",
            )
        )

    table = Table(
        show_header=True,
        title=f"[cyan]{len(requirements)}[/cyan] Profile Requirements",
        title_style="italic bold",
        header_style="bold cyan",
        border_style="bright_black",
        show_footer=False,
        show_lines=True,
        caption_style="italic bold",
        caption=f"[cyan](*)[/cyan] number of checks by severity level: {', '.join(levels_list)}",
    )

    # Define columns
    table.add_column("#", style="cyan bold", justify="right")
    table.add_column("Name", style="hot_pink bold", justify="left")
    table.add_column("Description", style="white italic")
    table.add_column("# REQUIRED", style=__requirement_level_style__(LevelCollection.REQUIRED), justify="center")
    table.add_column("# RECOMMENDED", style=__requirement_level_style__(LevelCollection.RECOMMENDED), justify="center")
    table.add_column("# OPTIONAL", style=__requirement_level_style__(LevelCollection.OPTIONAL), justify="center")
    # Add data to the table
    for row in table_rows:
        table.add_row(*row)
    return table


def __verbose_describe_profile__(profile):
    """
    Show a profile in a verbose way
    """
    table_rows = []
    levels_list = set()
    count_checks = 0
    for effective_check in profile.get_effective_requirement_checks():
        check = effective_check.check
        if check.requirement.hidden:
            continue
        color = get_severity_color(check.severity)
        level_info = f"[{color}]{check.severity.name}[/{color}]"
        levels_list.add(level_info)
        relation = __format_check_relation__(effective_check)
        table_rows.append(
            (
                effective_check.identifier,
                check.name,
                relation,
                effective_check.source_identifier,
                Markdown(check.description.strip()),
                level_info,
            )
        )
        count_checks += 1

    table = Table(
        show_header=True,
        title=f"[cyan]{count_checks}[/cyan] Profile Requirements Checks",
        title_style="italic bold",
        header_style="bold cyan",
        border_style="bright_black",
        show_footer=False,
        show_lines=True,
        caption_style="italic bold",
        caption=(
            f"[cyan](*)[/cyan] number of checks by severity level: {', '.join(levels_list)}\n"
            "[cyan](†)[/cyan] Effective ID is the identity exposed by this profile; "
            "Source ID identifies the check implementation"
        ),
    )

    # Define columns
    table.add_column("Effective ID (†)", style="cyan bold", justify="right")
    table.add_column("Name", style="hot_pink bold", justify="left")
    table.add_column("Relation", justify="left")
    table.add_column("Source ID (†)", style="magenta italic", justify="right")
    table.add_column("Description", style="white italic")
    table.add_column("Severity (*)", style="bold", justify="center")

    # Add data to the table
    for row in table_rows:
        table.add_row(*row)
    return table


_CHECK_ID_RE = re.compile(r"^(?P<req>\d+)\.(?P<check>\d+)$")


def __resolve_check__(profile: Profile, check_identifier: str) -> EffectiveRequirementCheck:
    """
    Resolve a check identifier to its effective profile view.
    Accepts either the relative form ``<req#>.<check#>`` or the full form
    ``<profile>_<req#>.<check#>``.
    """
    raw = check_identifier.strip()
    effective_checks = tuple(
        item for item in profile.get_effective_requirement_checks() if not item.check.requirement.hidden
    )
    if "_" in raw:
        match = next((item for item in effective_checks if item.identifier == raw), None)
        if match is None:
            raise click.BadParameter(
                f"Check identifier '{raw}' is not part of effective profile '{profile.identifier}'.",
                param_hint="CHECK_IDENTIFIER",
            )
        return match

    if not _CHECK_ID_RE.match(raw):
        raise click.BadParameter(
            f"Invalid check identifier '{check_identifier}'. "
            f"Expected '<requirement#>.<check#>' (e.g. '1.2') or "
            f"'<profile>_<requirement#>.<check#>' (e.g. '{profile.identifier}_1.2').",
            param_hint="CHECK_IDENTIFIER",
        )
    matches = [item for item in effective_checks if item.identifier.rsplit("_", maxsplit=1)[-1] == raw]
    if not matches:
        raise click.BadParameter(
            f"No effective check '{raw}' in profile '{profile.identifier}'. "
            f"Run `rocrate-validator profiles describe {profile.identifier} -v` to list checks.",
            param_hint="CHECK_IDENTIFIER",
        )
    if len(matches) > 1:
        raise click.BadParameter(
            f"Relative check identifier '{raw}' is ambiguous in effective profile '{profile.identifier}'. "
            "Use one of the full effective identifiers shown by the verbose profile description.",
            param_hint="CHECK_IDENTIFIER",
        )
    return matches[0]


def __format_check_relation__(effective_check: EffectiveRequirementCheck) -> str:
    """Format the provenance relation of an effective check."""
    if effective_check.relation == RequirementCheckRelation.DEFINED_LOCALLY:
        return "[bold yellow]Defined locally[/bold yellow]"
    if effective_check.relation == RequirementCheckRelation.INHERITED:
        return (
            f"[bold cyan]Inherited[/bold cyan] from "
            f"[italic magenta]{effective_check.source_profile.identifier}[/italic magenta]"
        )
    replaced = ", ".join(check.identifier for check in effective_check.replaces)
    return f"[bold orange1]Replaces[/bold orange1] [italic magenta]{replaced}[/italic magenta]"


def __describe_check__(
    console, profile: Profile, effective_check: EffectiveRequirementCheck, verbose: bool = False
) -> None:
    """
    Render a single requirement check.
    """
    check = effective_check.check
    severity_color = get_severity_color(check.severity)
    requirement = check.requirement

    header = (
        f"[bold cyan]Profile:[/bold cyan] "
        f"[italic magenta]{profile.identifier}[/italic magenta]\n"
        f"[bold cyan]Effective ID:[/bold cyan] "
        f"[italic green]{effective_check.identifier}[/italic green]\n"
        f"[bold cyan]Name:[/bold cyan] [italic hot_pink]{check.name}[/italic hot_pink]\n"
        f"[bold cyan]Severity:[/bold cyan] "
        f"[bold {severity_color}]{check.severity.name}[/bold {severity_color}]\n"
        f"[bold cyan]Requirement:[/bold cyan] "
        f"[italic hot_pink]#{requirement.order_number} — {requirement.name}[/italic hot_pink]"
    )
    if requirement.path:
        header += f"\n[bold cyan]Source file:[/bold cyan] [italic green]{shorten_path(requirement.path)}[/italic green]"

    title = f"[bold][cyan]Check:[/cyan] [magenta italic]{effective_check.identifier}[/magenta italic][/bold]"
    console.print(
        Padding(
            Panel(header, title=title, padding=(1, 1, 1, 1), title_align="left", border_style="cyan"),
            (0, 1, 0, 1),
        )
    )

    description_panel = Panel(
        Markdown(check.description.strip()),
        title="[bold cyan]Description[/bold cyan]",
        title_align="left",
        border_style="bright_black",
        padding=(1, 1, 1, 1),
    )
    console.print(Padding(description_panel, (1, 1, 0, 1)))

    provenance = (
        f"[bold cyan]Relation:[/bold cyan] {__format_check_relation__(effective_check)}\n"
        f"[bold cyan]Effective ID:[/bold cyan] [italic cyan]{effective_check.identifier}[/italic cyan]\n"
        f"[bold cyan]Source ID:[/bold cyan] [italic magenta]{effective_check.source_identifier}[/italic magenta]\n"
        f"[bold cyan]Source profile:[/bold cyan] "
        f"[italic magenta]{effective_check.source_profile.identifier}[/italic magenta]"
    )
    console.print(
        Padding(
            Panel(
                provenance,
                title="[bold cyan]Provenance[/bold cyan]",
                title_align="left",
                border_style="bright_black",
                padding=(1, 1, 1, 1),
            ),
            (1, 1, 0, 1),
        )
    )

    if verbose:
        snippet = check.get_source_snippet()
        if snippet is None:
            console.print(
                Padding(
                    Panel(
                        "[italic]Source code not available for this check kind.[/italic]",
                        title="[bold cyan]Source[/bold cyan]",
                        title_align="left",
                        border_style="bright_black",
                        padding=(1, 1, 1, 1),
                    ),
                    (1, 1, 0, 1),
                )
            )
        else:
            source_title = f"[bold cyan]Source ({snippet.language})[/bold cyan]"
            if snippet.source_path:
                source_title += f': [italic green]"{snippet.source_path.name}"[/italic green]'
            console.print(
                Padding(
                    Panel(
                        Syntax(
                            snippet.code,
                            snippet.language,
                            theme="ansi_dark",
                            line_numbers=False,
                            word_wrap=True,
                        ),
                        title=source_title,
                        title_align="left",
                        border_style="bright_black",
                        padding=(1, 1, 1, 1),
                    ),
                    (1, 1, 1, 1),
                )
            )
