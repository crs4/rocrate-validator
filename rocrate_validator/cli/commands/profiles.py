import logging

from rich.markdown import Markdown
from rich.table import Table

from ... import services
from ...colors import get_severity_color
from ..main import cli, click

# set up logging
logger = logging.getLogger(__name__)


@cli.group("profiles")
@click.option(
    "-p",
    "--profiles-path",
    type=click.Path(exists=True),
    default="./profiles",
    show_default=True,
    help="Path containing the profiles files"
)
@click.pass_context
def profiles(ctx, profiles_path: str = "./profiles"):
    """
    [magenta]rocrate-validator:[/magenta] Manage profiles
    """


@profiles.command("list")
@click.pass_context
def list_profiles(ctx, profiles_path: str = "./profiles"):
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
@click.argument("profile-name", type=click.STRING, default="ro-crate", required=True)
@click.pass_context
def describe_profile(ctx,
                     profile_name: str = "ro-crate",
                     profiles_path: str = "./profiles"):
    """
    Show a profile
    """
    console = ctx.obj['console']
    # Get the profile
    try:
        profile = services.get_profile(profiles_path=profiles_path, profile_name=profile_name)

        console.print("\n", style="white bold")
        console.print(f"[bold]Profile: {profile_name}[/bold]", style="magenta bold")
        console.print("\n", style="white bold")
        console.print(Markdown(profile.description.strip()))
        console.print("\n", style="white bold")

        table_rows = []
        levels_list = set()
        for requirement in profile.requirements:
            color = get_severity_color(requirement.severity)
            level_info = f"[{color}]{requirement.severity.name}[/{color}]"
            levels_list.add(level_info)
            table_rows.append((str(requirement.order_number), requirement.name,
                              Markdown(requirement.description.strip()),
                              str(len(requirement.get_checks())),
                              level_info))

        table = Table(show_header=True,
                      title="Profile Requirements",
                      header_style="bold cyan",
                      border_style="bright_black",
                      show_footer=False,
                      caption=f"(*) Requirement level: {', '.join(levels_list)}")

        # Define columns
        table.add_column("#", style="yellow bold", justify="right")
        table.add_column("Name", style="magenta bold", justify="center")
        table.add_column("Description", style="white italic")
        table.add_column("# Checks", style="white", justify="center")
        table.add_column("Requirement Level (*)", style="white", justify="center")
        # Add data to the table
        for row in table_rows:
            table.add_row(*row)
        # Print the table
        console.print(table)
    except Exception as e:
        console.print(f"\n[red]ERROR:[/red] {e}\n", style="white")
        if logger.isEnabledFor(logging.DEBUG):
            console.print_exception(show_locals=True)
        ctx.exit(1)
