# Copyright (c) 2024 CRS4
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

import sys
from pathlib import Path

from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table

import rocrate_validator.log as logging
from rocrate_validator import services
from rocrate_validator.cli.commands.errors import handle_error
from rocrate_validator.cli.main import cli, click
from rocrate_validator.cli.utils import get_app_header_rule
from rocrate_validator.colors import get_severity_color
from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.models import (LevelCollection, RequirementLevel,
                                      Severity)
from rocrate_validator.utils import get_profiles_path

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
    help="Path containing the profiles files"
)
@click.pass_context
def profiles(ctx, profiles_path: Path = DEFAULT_PROFILES_PATH):
    """
    [magenta]rocrate-validator:[/magenta] Manage profiles
    """
    logger.debug("Profiles path: %s", profiles_path)
    ctx.obj['profiles_path'] = profiles_path


@profiles.command("list")
@click.option(
    '--no-paging',
    is_flag=True,
    help="Disable paging",
    default=False,
    show_default=True,
    hidden=True if sys.platform == "win32" else False
)
@click.pass_context
def list_profiles(ctx, no_paging: bool = False):  # , profiles_path: Path = DEFAULT_PROFILES_PATH):
    """
    List available profiles
    """
    profiles_path = ctx.obj['profiles_path']
    console = ctx.obj['console']
    pager = ctx.obj['pager']
    interactive = ctx.obj['interactive']
    # Get the no_paging flag
    enable_pager = not no_paging
    # override the enable_pager flag if the interactive flag is False
    if not interactive or sys.platform == "win32":
        enable_pager = False

    try:
        # Get the profiles
        profiles = services.get_profiles(profiles_path=profiles_path)

        table = Table(show_header=True,
                      title="   Available profiles",
                      title_style="italic bold cyan",
                      title_justify="left",
                      header_style="bold cyan",
                      border_style="bright_black",
                      show_footer=False,
                      caption_style="italic bold",
                      caption="[cyan](*)[/cyan] Number of requirements checks by severity")

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
            checks_info = {}
            for level in levels:
                checks_info[level.severity.name] = {
                    "count": 0,
                    "color": get_severity_color(level.severity)
                }

            requirements = [_ for _ in profile.get_requirements(severity=Severity.OPTIONAL) if not _.hidden]
            for requirement in requirements:
                for level in levels:
                    count = len(requirement.get_checks_by_level(level))
                    checks_info[level.severity.name]["count"] += count

            checks_summary = "\n".join(
                [f"[{v['color']}]{k}[/{v['color']}]: {v['count']}" for k, v in checks_info.items()])

            # Add the row to the table
            table.add_row(profile.identifier, profile.uri, profile.version,
                          profile.name, Markdown(profile.description.strip()),
                          "\n".join([p.identifier for p in profile.inherited_profiles]),
                          checks_summary)
            table.add_row()

        # Print the table
        with console.pager(pager=pager, styles=not console.no_color) if enable_pager else console:
            console.print(get_app_header_rule())
            console.print(Padding(table, (0, 1)))

    except Exception as e:
        handle_error(e, console)


@profiles.command("describe")
@click.option(
    '-v',
    '--verbose',
    is_flag=True,
    help="Show detailed list of requirements",
    default=False,
    show_default=True
)
@click.argument("profile-identifier", type=click.STRING, default=DEFAULT_PROFILE_IDENTIFIER, required=True)
@click.option(
    '--no-paging',
    is_flag=True,
    help="Disable paging",
    default=False,
    show_default=True,
    hidden=True if sys.platform == "win32" else False
)
@click.pass_context
def describe_profile(ctx,
                     profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER,
                     profiles_path: Path = DEFAULT_PROFILES_PATH,
                     verbose: bool = False, no_paging: bool = False):
    """
    Show a profile
    """
    # Get the console
    console = ctx.obj['console']
    pager = ctx.obj['pager']
    interactive = ctx.obj['interactive']
    profiles_path = ctx.obj['profiles_path']
    # Get the no_paging flag
    enable_pager = not no_paging
    # override the enable_pager flag if the interactive flag is False
    if not interactive or sys.platform == "win32":
        enable_pager = False

    try:
        # Get the profile
        profile = services.get_profile(profiles_path=profiles_path, profile_identifier=profile_identifier)

        # Set the subheader title
        subheader_title = f"[bold][cyan]Profile:[/cyan] [magenta italic]{profile.identifier}[/magenta italic][/bold]"

        # Set the subheader content
        subheader_content = f"[bold cyan]Version:[/bold cyan] [italic green]{profile.version}[/italic green]\n"
        subheader_content += f"[bold cyan]URI:[/bold cyan] [italic yellow]{profile.uri}[/italic yellow]\n\n"
        subheader_content += f"[bold cyan]Description:[/bold cyan] [italic]{profile.description.strip()}[/italic]"

        # Build the profile table
        if not verbose:
            table = __compacted_describe_profile__(profile)
        else:
            table = __verbose_describe_profile__(profile)

        with console.pager(pager=pager, styles=not console.no_color) if enable_pager else console:
            console.print(get_app_header_rule())
            console.print(Padding(Panel(subheader_content, title=subheader_title, padding=(1, 1),
                                        title_align="left", border_style="cyan"), (0, 1, 0, 1)))
            console.print(Padding(table, (1, 1)))

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
        table_rows.append((str(requirement.order_number), requirement.name,
                           Markdown(requirement.description.strip()),
                           f"{levels_count[0]}",
                           f"{levels_count[1]}",
                           f"{levels_count[2]}"))

    table = Table(show_header=True,
                  #   renderer=renderer,
                  title=f"[cyan]{len(requirements)}[/cyan] Profile Requirements",
                  title_style="italic bold",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False,
                  show_lines=True,
                  caption_style="italic bold",
                  caption=f"[cyan](*)[/cyan] number of checks by severity level: {', '.join(levels_list)}")

    # Define columns
    table.add_column("#", style="cyan bold", justify="right")
    table.add_column("Name", style="magenta bold", justify="left")
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
    for requirement in profile.requirements:
        # skip hidden requirements
        if requirement.hidden:
            continue
        # add the requirement to the list
        for check in requirement.get_checks():
            color = get_severity_color(check.severity)
            level_info = f"[{color}]{check.severity.name}[/{color}]"
            levels_list.add(level_info)
            override = None
            # Uncomment the following lines to show the overridden checks
            # if check.overridden_by:
            #     logger.debug("Check %s is overridden by: %s", check.identifier, check.overridden_by)
            #     override = "[overridden by: "
            #     for co in check.overridden_by:
            #         severity_color = get_severity_color(co.severity)
            #         override += f"[bold][magenta]{co.requirement.profile.identifier}[/magenta] "\
            #             f"[{severity_color}]{co.relative_identifier}[/{severity_color}][/bold]"
            #         if co != check.overridden_by[-1]:
            #             override += ", "
            #     override += "]"
            if check.override:
                logger.debug("Check %s overrides: %s", check.identifier, check.override)
                override = "[" + "overrides: "
                for co in check.override:
                    severity_color = get_severity_color(co.severity)
                    override += f"[bold][magenta]{co.requirement.profile.identifier}[/magenta] "\
                        f"[{severity_color}]{co.relative_identifier}[/{severity_color}][/bold]"
                    if co != check.override[-1]:
                        override += ", "
                override += "]"
            from rich.align import Align
            description_table = Table(show_header=False, show_footer=False, show_lines=False, show_edge=False)
            if override:
                description_table.add_row(Align(Padding(override, (0, 0, 1, 0)), align="right"))
            description_table.add_row(Markdown(check.description.strip()))

            table_rows.append((str(check.relative_identifier), check.name,
                               description_table, level_info))
            count_checks += 1

    table = Table(show_header=True,
                  #   renderer=renderer,
                  title=f"[cyan]{count_checks}[/cyan] Profile Requirements Checks",
                  title_style="italic bold",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False,
                  show_lines=True,
                  caption_style="italic bold",
                  caption=f"[cyan](*)[/cyan] number of checks by severity level: {', '.join(levels_list)}")

    # Define columns
    table.add_column("Identifier", style="cyan bold", justify="right")
    table.add_column("Name", style="magenta bold", justify="left")
    table.add_column("Description", style="white italic")
    table.add_column("Severity (*)", style="bold", justify="center")

    # Add data to the table
    for row in table_rows:
        table.add_row(*row)
    return table
