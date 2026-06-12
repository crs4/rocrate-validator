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

from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from rocrate_validator.models import (
    ProfileValidationEvent,
    RequirementCheckValidationEvent,
    RequirementValidationEvent,
    ValidationContext,
    ValidationSettings,
    ValidationStatistics,
)
from rocrate_validator.utils import log as logging

from .dispatcher import EventDispatcher

# set up logging
logger = logging.getLogger(__name__)


class ProgressMonitor(EventDispatcher):
    PROFILE_VALIDATION = "Profiles"
    REQUIREMENT_VALIDATION = "Requirements"
    REQUIREMENT_CHECK_VALIDATION = "Requirements Checks"

    def __init__(self, settings: dict | ValidationSettings, stats: ValidationStatistics | None = None):
        # Initialize the Subscriber
        super().__init__("ProgressMonitor")
        self.__progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            expand=True,
        )
        # Initialize statistics
        stats = stats or ValidationStatistics(settings)
        self.initial_state = stats
        # Store settings
        self.settings = settings
        # Initialize progress tasks
        self.profile_validation = self.__progress.add_task(self.PROFILE_VALIDATION, total=len(stats.profiles))
        self.requirement_validation = self.__progress.add_task(
            self.REQUIREMENT_VALIDATION, total=stats.total_requirements
        )
        self.requirement_check_validation = self.__progress.add_task(
            self.REQUIREMENT_CHECK_VALIDATION, total=stats.total_checks
        )
        # Initialize progress according to current statistics
        self.__progress.update(task_id=self.profile_validation, advance=len(stats.validated_profiles))
        self.__progress.update(task_id=self.requirement_validation, advance=len(stats.validated_requirements))
        self.__progress.update(task_id=self.requirement_check_validation, advance=len(stats.validated_checks))

    def start(self):
        self.__progress.start()

    def stop(self):
        self.__progress.stop()

    @property
    def progress(self) -> Progress:
        return self.__progress

    def _on_requirement_check_validation_end(
        self, event: RequirementCheckValidationEvent, ctx: ValidationContext | None
    ) -> None:
        self.__progress.update(task_id=self.requirement_check_validation, advance=1)

    def _on_requirement_validation_end(self, event: RequirementValidationEvent, ctx: ValidationContext | None) -> None:
        self.__progress.update(task_id=self.requirement_validation, advance=1)

    def _on_profile_validation_end(self, event: ProfileValidationEvent, ctx: ValidationContext | None) -> None:
        self.__progress.update(task_id=self.profile_validation, advance=1)
