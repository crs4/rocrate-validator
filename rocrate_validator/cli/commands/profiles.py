from pathlib import Path

from rich.markdown import Markdown
from rich.table import Table

import rocrate_validator.log as logging
from rocrate_validator import services
from rocrate_validator.cli.main import cli, click
from rocrate_validator.colors import get_severity_color
from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.models import (LevelCollection,
                                      RequirementLevel)
from rocrate_validator.utils import get_profiles_path

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


@cli.group("profiles")
@click.option(
    "-p",
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
@click.pass_context
def list_profiles(ctx):  # , profiles_path: Path = DEFAULT_PROFILES_PATH):
    """
    List available profiles
    """
    profiles_path = ctx.obj['profiles_path']
    console = ctx.obj['console']
    # Get the profiles
    profiles = services.get_profiles(profiles_path=profiles_path)
    # console.print("\nAvailable profiles:", style="white bold")
    console.print("\n", style="white bold")

    table = Table(show_header=True,
                  title="Available profiles",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False,
                  caption="[cyan](*)[/cyan] Number of requirements by severity")

    # Define columns
    table.add_column("Identifier", style="magenta bold", justify="center")
    table.add_column("URI", style="yellow bold", justify="center")
    table.add_column("Name", style="white bold", justify="center")
    table.add_column("Description", style="white italic")
    table.add_column("based on", style="white", justify="center")
    table.add_column("Requirements (*)", style="white", justify="center")

    # Add data to the table
    for profile in profiles:
        # Count requirements by severity
        requirements = {}
        logger.debug("Requirements: %s", requirements)
        for req in profile.requirements:
            if not requirements.get(req.severity.name, None):
                requirements[req.severity.name] = 0
            requirements[req.severity.name] += 1
        requirements = ", ".join(
            [f"[bold][{get_severity_color(severity)}]{severity}: "
             f"{count}[/{get_severity_color(severity)}][/bold]"
             for severity, count in requirements.items() if count > 0])

        # Add the row to the table
        table.add_row(__format_version_identifier__(profile), profile.uri,
                      profile.name, Markdown(profile.description.strip()),
                      ", ".join([p.identifier for p in profile.inherited_profiles]),
                      requirements)
        table.add_row()

    # Print the table
    console.print(table)


def __format_version_identifier__(profile):
    """
    Format the version and identifier
    """

    table = Table(show_header=True,
                  title=profile.identifier,
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False)
    table.add_column("prefix", style="magenta bold", justify="center")
    table.add_column("version", style="yellow bold", justify="center")

    table.add_row(profile.token, profile.version)
    return table


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
@click.pass_context
def describe_profile(ctx,
                     profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER,
                     profiles_path: Path = DEFAULT_PROFILES_PATH,
                     verbose: bool = False):
    """
    Show a profile
    """
    console = ctx.obj['console']
    # Get the profile
    profile = services.get_profile(profiles_path=profiles_path, profile_identifier=profile_identifier)
    console.print("\n", style="white bold")
    console.print(f"[bold]Profile: {profile_identifier}[/bold]", style="magenta bold")
    console.print("\n", style="white bold")
    console.print(Markdown(profile.description.strip()))
    console.print("\n", style="white bold")

    if not verbose:
        __compacted_describe_profile__(console, profile)
    else:
        __verbose_describe_profile__(console, profile)


def __requirement_level_style__(requirement: RequirementLevel):
    """
    Format the requirement level
    """
    color = get_severity_color(requirement.severity)
    return f"{color} bold"


def __compacted_describe_profile__(console, profile):
    """
    Show a profile in a compact way
    """
    table_rows = []
    levels_list = set()
    for requirement in profile.requirements:
        # skip hidden requirements
        if requirement.hidden:
            continue
        # add the requirement to the list
        color = get_severity_color(requirement.severity)
        level_info = f"[{color}]{requirement.severity.name}[/{color}]"
        levels_list.add(level_info)
        table_rows.append((str(requirement.order_number), requirement.name,
                           Markdown(requirement.description.strip()),
                           f"{len(requirement.get_checks_by_level(LevelCollection.REQUIRED))}",
                           f"{len(requirement.get_checks_by_level(LevelCollection.RECOMMENDED))}",
                           f"{len(requirement.get_checks_by_level(LevelCollection.OPTIONAL))}"))

    table = Table(show_header=True,
                  title="Profile Requirements",
                  title_style="italic bold",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False,
                  show_lines=True,
                  caption=f"[cyan](*)[/cyan] number of checks by severity level: {', '.join(levels_list)}",
                  caption_style="italic bold")

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
    # Print the table
    console.print(table)


def __verbose_describe_profile__(console, profile):
    """
    Show a profile in a verbose way
    """
    table_rows = []
    levels_list = set()
    for requirement in profile.requirements:
        # skip hidden requirements
        if requirement.hidden:
            continue
        # add the requirement to the list
        for check in requirement.get_checks():
            color = get_severity_color(check.severity)
            level_info = f"[{color}]{check.severity.name}[/{color}]"
            levels_list.add(level_info)
            logger.debug("Check %s: %s", check.name, check.description)
            # checks.append(check)
            table_rows.append((str(check.identifier).rjust(14), check.name,
                               Markdown(check.description.strip()), level_info))

    table = Table(show_header=True,
                  title="Profile Requirements Checks",
                  title_style="italic bold",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False,
                  show_lines=True,
                  caption=f"[cyan](*)[/cyan] severity level of requirement check: {', '.join(levels_list)}",
                  caption_style="italic bold")

    # Define columns
    table.add_column("Identifier", style="cyan bold", justify="right")
    table.add_column("Name", style="magenta bold", justify="left")
    table.add_column("Description", style="white italic")
    table.add_column("Severity (*)", style="bold", justify="center")

    # Add data to the table
    for row in table_rows:
        table.add_row(*row)
    # Print the table
    console.print(table)
