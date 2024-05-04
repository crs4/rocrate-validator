import logging
from pathlib import Path

from rich.markdown import Markdown
from rich.table import Table

from rocrate_validator import services
from rocrate_validator.cli.main import cli, click
from rocrate_validator.colors import get_severity_color
from rocrate_validator.constants import DEFAULT_PROFILE_NAME
from rocrate_validator.models import LevelCollection, Requirement, RequirementLevel
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


@profiles.command("list")
@click.pass_context
def list_profiles(ctx, profiles_path: Path = DEFAULT_PROFILES_PATH):
    """
    List available profiles
    """
    console = ctx.obj['console']
    profiles = services.get_profiles(profiles_path=profiles_path)
    # console.print("\nAvailable profiles:", style="white bold")
    console.print("\n", style="white bold")

    table = Table(show_header=True,
                  title="Available profiles",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False,
                  caption="(*) Number of requirements by severity")

    # Define columns
    table.add_column("Name", style="magenta bold", justify="right")
    table.add_column("Description", style="white italic")
    table.add_column("Requirements (*)", style="white", justify="center")

    # Add data to the table
    for profile_name, profile in profiles.items():
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
        table.add_row(profile_name, Markdown(profile.description.strip()), requirements)
        table.add_row()

    # Print the table
    console.print(table)


@profiles.command("describe")
@click.option(
    '-v',
    '--verbose',
    is_flag=True,
    help="Show detailed list of requirements",
    default=False,
    show_default=True
)
@click.argument("profile-name", type=click.STRING, default=DEFAULT_PROFILE_NAME, required=True)
@click.pass_context
def describe_profile(ctx,
                     profile_name: str = DEFAULT_PROFILE_NAME,
                     profiles_path: Path = DEFAULT_PROFILES_PATH,
                     verbose: bool = False):
    """
    Show a profile
    """
    console = ctx.obj['console']
    # Get the profile
    profile = services.get_profile(profiles_path=profiles_path, profile_name=profile_name)

    console.print("\n", style="white bold")
    console.print(f"[bold]Profile: {profile_name}[/bold]", style="magenta bold")
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
                  caption=f"(*) number of checks by severity level: {', '.join(levels_list)}",
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

        for check in requirement.get_checks():
            color = get_severity_color(check.severity)
            level_info = f"[{color}]{check.severity.name}[/{color}]"
            levels_list.add(level_info)
            logger.debug("Check %s: %s", check.name, check.description)
            # checks.append(check)
            table_rows.append((str(check.identifier).rjust(14), check.name,
                               Markdown(check.description.strip()), level_info))

    table = Table(show_header=True,
                  title="Profile Requirements",
                  title_style="italic bold",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=False,
                  show_lines=True,
                  caption=f"[cyan](*)[/cyan] severity level of requirement: {', '.join(levels_list)}",
                  caption_style="italic bold")

    # Define columns
    table.add_column("Identifier", style="yellow bold", justify="right")
    table.add_column("Name", style="magenta bold", justify="left")
    table.add_column("Description", style="white italic")
    table.add_column("Severity (*)", style="bold", justify="center")

    # Add data to the table
    for row in table_rows:
        table.add_row(*row)
    # Print the table
    console.print(table)
