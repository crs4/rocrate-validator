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
from typing import Optional

import rich_click as click
from rich.padding import Padding
from rich.rule import Rule

from rocrate_validator.utils import log as logging
from rocrate_validator import services
from rocrate_validator.cli.commands.errors import handle_error
from rocrate_validator.cli.main import cli
from rocrate_validator.cli.ui.text.validate import ValidationCommandView
from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.utils.io_helpers.input import get_single_char, multiple_choice
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.utils.io_helpers.output.json import JSONOutputFormatter
from rocrate_validator.utils.io_helpers.output.text import TextOutputFormatter
from rocrate_validator.utils.io_helpers.output.text.layout.report import (
    LiveTextProgressLayout, get_app_header_rule)
from rocrate_validator.models import (Severity, ValidationResult,
                                      ValidationSettings)
from rocrate_validator.utils.uri import validate_rocrate_uri
from rocrate_validator.utils.paths import get_profiles_path

# from rich.markdown import Markdown
# from rich.table import Table

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


def validate_uri(ctx, param, value):
    """
    Validate if the value is a path or a URI
    """
    if value:
        try:
            validate_rocrate_uri(value)
        except ROCrateInvalidURIError as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            raise click.BadParameter(e.message, param=param)
    return value


@cli.command("validate")
@click.argument("rocrate-uri", callback=validate_uri, default=".")
@click.option(
    '-rr',
    '--relative-root-path',
    help="Use root-relative paths for all file references in the RO-Crate",
    default=None,
    show_default=True
)
@click.option(
    '-m',
    '--metadata-only',
    is_flag=True,
    help="Validate only the metadata of the RO-Crate",
    default=False,
    show_default=True
)
@click.option(
    '-ff',
    '--fail-fast',
    is_flag=True,
    help="Fail fast validation mode",
    default=False,
    show_default=True
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
    help="Path containing additional user profiles files"
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
    show_default=True
)
@click.option(
    '-nh',
    '--disable-profile-inheritance',
    is_flag=True,
    help="Disable inheritance of profiles",
    default=False,
    show_default=True
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
    '-lo',
    '--requirement-severity-only',
    is_flag=True,
    help="Validate only the requirements of the specified severity (no requirements with lower severity)",
    default=False,
    show_default=True
)
@click.option(
    '-s',
    '--skip-checks',
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
    '-v',
    '--verbose',
    is_flag=True,
    help="Output the validation details without prompting",
    default=False,
    show_default=True
)
@click.option(
    '--no-paging',
    is_flag=True,
    help="Disable pagination of the validation details",
    default=False,
    show_default=True,
    hidden=True if sys.platform == "win32" else False
)
@click.option(
    '-f',
    '--output-format',
    type=click.Choice(["json", "text"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Output format of the validation report"
)
@click.option(
    '-o',
    '--output-file',
    type=click.Path(),
    default=None,
    show_default=True,
    help="Path to the output file for the validation report",
)
@click.option(
    '-w',
    '--output-line-width',
    type=click.INT,
    default=120,
    show_default=True,
    help="Width of the output line",
)
@click.pass_context
def validate(ctx,
             profiles_path: Path = DEFAULT_PROFILES_PATH,
             extra_profiles_path: Optional[Path] = None,
             profile_identifier: Optional[str] = None,
             metadata_only: bool = False,
             no_auto_profile: bool = False,
             disable_profile_inheritance: bool = False,
             requirement_severity: str = Severity.REQUIRED.name,
             requirement_severity_only: bool = False,
             skip_checks: list[str] = None,
             rocrate_uri: Path = ".",
             relative_root_path: Optional[Path] = None,
             fail_fast: bool = False,
             no_paging: bool = False,
             verbose: bool = False,
             output_format: str = "text",
             output_file: Optional[Path] = None,
             output_line_width: Optional[int] = None):
    """
    [magenta]rocrate-validator:[/magenta] Validate a RO-Crate against a profile
    """
    console: Console = ctx.obj['console']
    pager = ctx.obj['pager']
    interactive = ctx.obj['interactive']
    # Get the no_paging flag
    enable_pager = not no_paging
    # override the enable_pager flag if the interactive flag is False
    if not interactive or sys.platform == "win32":
        enable_pager = False
    # Log the input parameters for debugging
    logger.debug("profiles_path: %s", os.path.abspath(profiles_path))
    logger.debug("extra_profiles_path: %s", os.path.abspath(extra_profiles_path) if extra_profiles_path else None)
    logger.debug("profile_identifier: %s", profile_identifier)
    logger.debug("requirement_severity: %s", requirement_severity)
    logger.debug("requirement_severity_only: %s", requirement_severity_only)

    logger.debug("disable_inheritance: %s", disable_profile_inheritance)
    logger.debug("rocrate_uri: %s", rocrate_uri)
    logger.debug("fail_fast: %s", fail_fast)
    logger.debug("no fail fast: %s", not fail_fast)

    if rocrate_uri:
        logger.debug("rocrate_path: %s", os.path.abspath(rocrate_uri))

    # Parse the skip_checks option
    logger.debug("skip_checks: %s", skip_checks)
    # Parse the skip_checks option
    skip_checks_list = []
    if skip_checks:
        try:
            for s in skip_checks:
                skip_checks_list.extend(_.strip() for _ in s.split(",") if _.strip())
            logger.debug("skip_checks_list: %s", skip_checks_list)
        except Exception as e:
            logger.error("Error parsing skip_checks: %s", e)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error parsing skip_checks: %s", e)
            raise ValueError(
                f"Invalid skip_checks value: {s}. "
                "It must be a comma-separated list of Fully Qualified Check IDs."
            )
    logger.debug("Skip checks: %s", skip_checks_list)

    try:
        # Validation settings
        validation_settings = {
            "profiles_path": profiles_path,
            "extra_profiles_path": extra_profiles_path,
            "profile_identifier": profile_identifier,
            "requirement_severity": requirement_severity,
            "requirement_severity_only": requirement_severity_only,
            "enable_profile_inheritance": not disable_profile_inheritance,
            "rocrate_uri": rocrate_uri,
            "rocrate_relative_root_path": relative_root_path,
            "abort_on_first": fail_fast,
            "skip_checks": skip_checks_list,
            "metadata_only": metadata_only
        }

        # Print the application header
        if output_format == "text" and output_file is None:
            console.print(get_app_header_rule())

        # Get the available profiles
        available_profiles = services.get_profiles(profiles_path, extra_profiles_path=extra_profiles_path)

        # Detect the profile to use for validation
        autodetection = False
        selected_profile = profile_identifier
        if selected_profile is None or len(selected_profile) == 0:

            # Auto-detect the profile to use for validation (if not disabled)
            candidate_profiles = None
            if not no_auto_profile:
                candidate_profiles = services.detect_profiles(settings=validation_settings)
                logger.debug("Candidate profiles: %s", candidate_profiles)
            else:
                logger.info("Auto-detection of the profiles to use for validation is disabled")

            # Prompt the user to select the profile to use for validation if the interactive mode is enabled
            # and no profile is auto-detected or multiple profiles are detected
            if interactive and (
                not candidate_profiles or
                len(candidate_profiles) == 0 or
                len(candidate_profiles) == len(available_profiles)
            ):
                # Define the list of choices
                console.print(
                    Padding(
                        Rule(
                            "[bold yellow]WARNING: [/bold yellow]"
                            "[bold]Unable to automatically detect the profile to use for validation[/bold]\n",
                            align="center",
                            style="bold yellow"
                        ),
                        (2, 2, 0, 2)
                    )
                )
                selected_options = multiple_choice(console, available_profiles)
                profile_identifier = [available_profiles[int(
                    selected_option)].identifier for selected_option in selected_options]
                logger.debug("Profile selected: %s", selected_options)
                console.print(Padding(Rule(style="bold yellow"), (1, 2)))

            elif candidate_profiles and len(candidate_profiles) < len(available_profiles):
                logger.debug("Profile identifier autodetected: %s", candidate_profiles[0].identifier)
                autodetection = True
                profile_identifier = [_.identifier for _ in candidate_profiles]

        # Fall back to the selected profile
        if not profile_identifier or len(profile_identifier) == 0:
            console.print(f"\n{' '*2}[bold yellow]WARNING: [/bold yellow]", end="")
            if no_auto_profile:
                console.print("[bold]Auto-detection of the profiles to use for validation is disabled[/bold]")
            else:
                console.print("[bold]Unable to automatically detect the profile to use for validation[/bold]")
            console.print(f"{' '*11}[bold]The base `ro-crate` profile will be used for validation[/bold]")
            profile_identifier = ["ro-crate"]

        # Validate the RO-Crate against the selected profiles
        is_valid = True
        results = {}
        for profile in profile_identifier:
            # Duplicate settings for each profile and set the profile identifier
            logger.info("\nValidating RO-Crate against profile: [bold cyan]%s[/bold cyan]", profile)
            validation_settings = validation_settings.copy()
            # Set the selected profile
            validation_settings["profile_identifier"] = profile
            logger.debug("Profile selected for validation: %s", validation_settings["profile_identifier"])
            logger.debug("Profile autodetected: %s", autodetection)

            # Initialize the validation result variable
            result: ValidationResult = None

            #########################################################################################
            # Perform and display the validation with progress bar to the console
            #########################################################################################
            # Perform the validation and get the validation result
            if output_format == "text" and not output_file:
                # If in interactive mode, show the validation progress with a progress bar
                # with a live updating layout
                if interactive:
                    # Initialize the command view for text output
                    command_view = ValidationCommandView(
                        validation_settings=ValidationSettings.parse(validation_settings),
                        console=console,
                        interactive=interactive,
                        no_paging=not enable_pager,
                        pager=pager
                    )
                    # Validate RO-Crate against the profile and get the validation result
                    result = command_view.show_validation_progress(services.validate)

                    # Print the validation result
                    if not result.passed():
                        verbose_choice = "n"
                        if interactive and not verbose:
                            verbose_choice = get_single_char(console, choices=['y', 'n'],
                                                             message=(
                                "[bold] > Do you want to see the validation details? "
                                "([magenta]y/n[/magenta]): [/bold]"
                            ))
                        if verbose_choice == "y" or verbose:
                            command_view.display_validation_result(result)
                else:
                    # Validate RO-Crate against the profile and get the validation result
                    result: ValidationResult = services.validate(validation_settings)
                    # Init TextOutputFormatter for console output
                    console.register_formatter(TextOutputFormatter())
                    # Show the final overview of the validation if no interactive mode
                    console.print(result.statistics)

                    # Print the validation result
                    if not result.passed() and verbose:
                        out = Console(no_color=console.no_color, width=console.width, height=console.height)
                        out.register_formatter(TextOutputFormatter())
                        out.print(result)

            ###########################################################################################
            # Perform the validation without progress bar (for JSON output or text output to file)
            ###########################################################################################
            else:
                # Notify the start of the validation
                if interactive:
                    with LiveTextProgressLayout(
                        console=console,
                        profile_identifier=profile,
                        validation_settings=validation_settings,
                        callable_service=services.validate,
                        transient=True
                    ) as result:
                        logger.debug("Validation result obtained")
                else:
                    # Validate RO-Crate against the profile and get the validation result
                    result: ValidationResult = services.validate(validation_settings)
                results[profile] = result

                # Output processing for text format to file
                ###################################################################################
                if output_file and output_format == "text":
                    if interactive:
                        console.print(f"\n{' '*2}📝 [bold]Writing validation results to file[/bold]{'.'*4} ", end="")
                    with open(output_file, "w", encoding="utf-8") if output_file else sys.stdout as f:
                        out = Console(color_system=None, width=output_line_width, height=31, file=f)
                        if output_format == "text":
                            out.register_formatter(TextOutputFormatter())
                            # Print the report layout
                            out.print(result.statistics)  # Output the statistics first
                            if not result.passed() and verbose:
                                out.print(result)
                    if interactive:
                        console.print(f"[bold green]{output_file}[/bold green]", end="\n")

            # Update the global validation status
            is_valid = is_valid and result.passed()

            # Interrupt the validation if the fail fast mode is enabled
            if fail_fast and not is_valid:
                break

        ###################################################################
        # ############## JSON OUTPUT FORMAT PROCESSING ################## #
        ###################################################################
        # Process JSON output format
        if output_format == "json":
            # Notify completion of the validation
            if interactive:
                if is_valid:
                    console.print(
                        f"\n{' '*2}✅ [bold]Validation [green]PASSED![/green]. "
                        f"\n{' '*5}RO-Crate is valid according to the profile(s): "
                        f"[cyan]{', '.join(profile_identifier)}[/cyan][/bold]"
                    )
                else:
                    console.print(f"\n{' '*2}❌ [bold]Validation [red]FAILED![/red][/bold]")
            # Notify the start of JSON output generation
            if interactive:
                if output_file:
                    console.print(
                        f"\n{' '*2}📝 [bold]Writing validation results in JSON format "
                        f"to the file \"{output_file}\"[/bold]{'.'*4} ",
                        end=""
                    )
                else:
                    console.print(f"\n{' '*2}📋 [bold]The validation report in JSON format: [/bold]\n")

            # Generate the JSON output and write it to the specified output file or to stdout
            with open(output_file, "w", encoding="utf-8") if output_file else sys.stdout as f:
                out = Console(width=output_line_width, file=f)
                out.register_formatter(JSONOutputFormatter())
                out.print(results)

            # Notify completion of JSON output generation
            if interactive and output_file:
                console.print("[bold]DONE![/bold]", end="\n\n")

        ################################################################################
        # Exit with appropriate status code
        ################################################################################

        # using ctx.exit seems to raise an Exception that gets caught below,
        # so we use sys.exit instead.
        sys.exit(0 if is_valid else 1)
    except Exception as e:
        handle_error(e, console)
