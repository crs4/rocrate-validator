import logging

from rich.markdown import Markdown
from rich.table import Table

from ... import services
from ...colors import get_severity_color
from .. import cli, click, console

# set up logging
logger = logging.getLogger(__name__)


@cli.group("profiles")
def profiles():
    """
    [magenta]rocrate-validator:[/magenta] Manage profiles
    """
    pass


@profiles.command("list")
@click.option(
    "-p",
    "--profiles-path",
    type=click.Path(exists=True),
    default="./profiles",
    show_default=True,
    help="Path containing the profiles files",
)
@click.pass_context
def list_profiles(ctx, profiles_path: str = "./profiles"):
    """
    List available profiles
    """
    profiles = services.get_profiles(profiles_path=profiles_path)
    # console.print("\nAvailable profiles:", style="white bold")
    console.print("\n", style="white bold")

    table = Table(show_header=True,
                  title="Available profiles",
                  header_style="bold cyan",
                  border_style="bright_black",
                  show_footer=True,
                  caption="(*) Number of requirements by severity")

    # Define columns
    table.add_column("Name", style="magenta bold")
    table.add_column("Description", style="white italic")
    table.add_column("Requirements (*)", style="white")

    # Add data to the table
    for profile_name, profile in profiles.items():
        # Count requirements by severity
        requirements = {}
        logger.debug("Requirements: %s", requirements)
        for req in profile.requirements:
            if not requirements.get(req.type.name, None):
                requirements[req.type.name] = 0
            requirements[req.type.name] += 1
        requirements = ", ".join(
            [f"[bold][{get_severity_color(severity)}]{severity}: "
             f"{count}[/{get_severity_color(severity)}][/bold]"
             for severity, count in requirements.items() if count > 0])

        # Add the row to the table
        table.add_row(profile_name, Markdown(profile.description.strip()), requirements)
        table.add_row()

    # Print the table
    console.print(table)
