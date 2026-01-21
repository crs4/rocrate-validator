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


from typing import Optional

from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from rocrate_validator.utils import log as logging
from rocrate_validator.events import Event, EventType, Subscriber
from rocrate_validator.models import ValidationContext, ValidationStatistics

# set up logging
logger = logging.getLogger(__name__)


class ProgressMonitor(Subscriber):

    PROFILE_VALIDATION = "Profiles"
    REQUIREMENT_VALIDATION = "Requirements"
    REQUIREMENT_CHECK_VALIDATION = "Requirements Checks"

    def __init__(self, settings: dict, stats: Optional[ValidationStatistics] = None):
        self.__progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            expand=True)
        # Initialize statistics
        stats = stats or ValidationStatistics(settings)
        self.initial_state = stats
        # Store settings
        self.settings = settings
        # Initialize progress tasks
        self.profile_validation = self.progress.add_task(
            self.PROFILE_VALIDATION, total=len(stats.profiles))
        self.requirement_validation = self.progress.add_task(
            self.REQUIREMENT_VALIDATION, total=stats.total_requirements)
        self.requirement_check_validation = self.progress.add_task(
            self.REQUIREMENT_CHECK_VALIDATION, total=stats.total_checks)

        # Initialize the Subscriber
        super().__init__("ProgressMonitor")

        # Initialize progress according to current statistics
        self.__initialize__(stats)

    def __initialize__(self, stats: ValidationStatistics):
        """Initialize the progress monitor according to the current statistics."""
        self.progress.update(task_id=self.profile_validation,
                             advance=len(stats.validated_profiles))
        self.progress.update(task_id=self.requirement_validation,
                             advance=len(stats.validated_requirements))
        self.progress.update(task_id=self.requirement_check_validation,
                             advance=len(stats.validated_checks))

    def start(self):
        self.progress.start()

    def stop(self):
        self.progress.stop()

    @property
    def progress(self) -> Progress:
        return self.__progress

    def update(self, event: Event, ctx: Optional[ValidationContext] = None):
        logger.debug("Event: %s", event.event_type)
        if event.event_type == EventType.VALIDATION_START:
            logger.debug("Validation started")
            # self.start()
        if event.event_type == EventType.PROFILE_VALIDATION_START:
            logger.debug("Profile validation start: %s", event.profile.identifier)
        elif event.event_type == EventType.REQUIREMENT_VALIDATION_START:
            logger.debug("Requirement validation start")
        elif event.event_type == EventType.REQUIREMENT_CHECK_VALIDATION_START:
            logger.debug("Requirement check validation start")
        elif event.event_type == EventType.REQUIREMENT_CHECK_VALIDATION_END:
            target_profile = ctx.target_validation_profile
            if not event.requirement_check.requirement.hidden and \
                    (not event.requirement_check.overridden
                     or target_profile.identifier == event.requirement_check.requirement.profile.identifier):
                self.progress.update(task_id=self.requirement_check_validation, advance=1)
            else:
                logger.debug("Skipping requirement check validation: %s", event.requirement_check.identifier)
        elif event.event_type == EventType.REQUIREMENT_VALIDATION_END:
            if not event.requirement.hidden:
                self.progress.update(task_id=self.requirement_validation, advance=1)
        elif event.event_type == EventType.PROFILE_VALIDATION_END:
            self.progress.update(task_id=self.profile_validation, advance=1)
        elif event.event_type == EventType.VALIDATION_END:
            logger.debug("Validation ended with result: %s", event.validation_result)
