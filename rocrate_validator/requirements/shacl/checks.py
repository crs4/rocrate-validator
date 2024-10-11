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

import json
from timeit import default_timer as timer
from typing import Optional

import rocrate_validator.log as logging
from rocrate_validator.errors import ROCrateMetadataNotFoundError
from rocrate_validator.events import EventType
from rocrate_validator.models import (LevelCollection, Requirement,
                                      RequirementCheck,
                                      RequirementCheckValidationEvent,
                                      SkipRequirementCheck, ValidationContext)
from rocrate_validator.requirements.shacl.models import Shape
from rocrate_validator.requirements.shacl.utils import make_uris_relative

from .validator import (SHACLValidationAlreadyProcessed,
                        SHACLValidationContext, SHACLValidationContextManager,
                        SHACLValidationSkip, SHACLValidator, SHACLViolation)

logger = logging.getLogger(__name__)


class SHACLCheck(RequirementCheck):
    """
    A SHACL check for a specific shape property
    """

    # Map shape to requirement check instances
    __instances__ = {}

    def __init__(self,
                 requirement: Requirement,
                 shape: Shape) -> None:
        self._shape = shape
        # init the check
        super().__init__(requirement,
                         shape.name if shape and shape.name
                         else shape.parent.name if shape.parent
                         else None,
                         shape.description if shape and shape.description
                         else shape.parent.description if shape.parent
                         else None)
        # store the instance
        SHACLCheck.__add_instance__(shape, self)

        # set the check level
        requirement_level_from_path = self.requirement.requirement_level_from_path
        if requirement_level_from_path:
            declared_level = shape.get_declared_level()
            if declared_level:
                if shape.level.severity != requirement_level_from_path.severity:
                    logger.warning("Mismatch in requirement level for check \"%s\": "
                                   "shape level %s does not match the level from the containing folder %s. "
                                   "Consider moving the shape property or removing the severity property.",
                                   self.name, shape.level, requirement_level_from_path)
        self._level = None

    @property
    def shape(self) -> Shape:
        return self._shape

    @property
    def description(self) -> str:
        return self._shape.description

    def __compute_requirement_level__(self) -> LevelCollection:
        if self._shape and self._shape.get_declared_level():
            return self._shape.get_declared_level()
        if self.requirement and self.requirement.requirement_level_from_path:
            return self.requirement.requirement_level_from_path
        return LevelCollection.REQUIRED

    @property
    def level(self) -> str:
        if not self._level:
            self._level = self.__compute_requirement_level__()
        return self._level

    @property
    def severity(self) -> str:
        return self.level.severity

    def execute_check(self, context: ValidationContext):
        logger.debug("Starting check %s", self)
        try:
            logger.debug("SHACL Validation of profile %s requirement %s started",
                         self.requirement.profile.identifier, self.identifier)
            with SHACLValidationContextManager(self, context) as ctx:
                # The check is executed only if the profile is the most specific one
                logger.debug("SHACL Validation of profile %s requirement %s started",
                             self.requirement.profile.identifier, self.identifier)
                result = self.__do_execute_check__(ctx)
                ctx.current_validation_result = self not in result
                return ctx.current_validation_result
        except SHACLValidationAlreadyProcessed:
            logger.debug("SHACL Validation of profile %s already processed", self.requirement.profile.identifier)
            # The check belongs to a profile which has already been processed
            # so we can skip the validation and return the specific result for the check
            return self not in [i.check for i in context.result.get_issues()]
        except SHACLValidationSkip as e:
            logger.debug("SHACL Validation of profile %s requirement %s skipped",
                         self.requirement.profile.identifier, self.identifier)
            # The validation is postponed to the more specific profiles
            # so the check is not considered as failed.
            raise SkipRequirementCheck(self, str(e))
        except ROCrateMetadataNotFoundError as e:
            logger.debug("Unable to perform metadata validation due to missing metadata file: %s", e)
            return False

    def __do_execute_check__(self, shacl_context: SHACLValidationContext):
        # get the shapes registry
        shapes_registry = shacl_context.shapes_registry

        # set up the input data for the validator
        start_time = timer()
        ontology_graph = shacl_context.ontology_graph
        end_time = timer()
        logger.debug(f"Execution time for getting ontology graph: {end_time - start_time} seconds")

        data_graph = None
        try:
            start_time = timer()
            data_graph = shacl_context.data_graph
            end_time = timer()
            logger.debug(f"Execution time for getting data graph: {end_time - start_time} seconds")
        except json.decoder.JSONDecodeError as e:
            logger.debug("Unable to perform metadata validation "
                         "due to one or more errors in the JSON-LD data file: %s", e)
            shacl_context.result.add_error(
                "Unable to perform metadata validation due to one or more errors in the JSON-LD data file", self)
            raise ROCrateMetadataNotFoundError(
                "Unable to perform metadata validation due to one or more errors in the JSON-LD data file")

        # Begin the timer
        start_time = timer()
        shapes_graph = shapes_registry.shapes_graph
        end_time = timer()
        logger.debug(f"Execution time for getting shapes: {end_time - start_time} seconds")

        # # uncomment to save the graphs to the logs folder (for debugging purposes)
        # start_time = timer()
        # data_graph.serialize("logs/data_graph.ttl", format="turtle")
        # shapes_graph.serialize("logs/shapes_graph.ttl", format="turtle")
        # if ontology_graph:
        #     ontology_graph.serialize("logs/ontology_graph.ttl", format="turtle")
        # end_time = timer()
        # logger.debug(f"Execution time for saving graphs: {end_time - start_time} seconds")

        # validate the data graph
        start_time = timer()
        shacl_validator = SHACLValidator(shapes_graph=shapes_graph, ont_graph=ontology_graph)
        shacl_result = shacl_validator.validate(
            data_graph=data_graph, ontology_graph=ontology_graph, **shacl_context.settings)
        # shacl_result.results_graph.serialize("logs/validation_results.ttl", format="turtle")
        # parse the validation result
        end_time = timer()
        logger.debug("Validation '%s' conforms: %s", self.name, shacl_result.conforms)
        logger.debug("Number of violations: %s", len(shacl_result.violations))
        logger.debug(f"Execution time for validating the data graph: {end_time - start_time} seconds")

        # store the validation result in the context
        start_time = timer()
        # if the validation fails, process the failed checks
        failed_requirements_checks = set()
        failed_requirements_checks_violations: dict[str, SHACLViolation] = {}
        failed_requirement_checks_notified = []
        logger.debug("Parsing Validation with result: %s", shacl_result)
        # process the failed checks to extract the requirement checks involved
        for violation in shacl_result.violations:
            shape = shapes_registry.get_shape(Shape.compute_key(shapes_graph, violation.sourceShape))
            assert shape is not None, "Unable to map the violation to a shape"
            requirementCheck = SHACLCheck.get_instance(shape)
            assert requirementCheck is not None, "The requirement check cannot be None"
            failed_requirements_checks.add(requirementCheck)
            violations = failed_requirements_checks_violations.get(requirementCheck.identifier, None)
            if violations is None:
                failed_requirements_checks_violations[requirementCheck.identifier] = violations = []
            violations.append(violation)
        # sort the failed checks by identifier and severity
        # to ensure a consistent order of the issues
        # and to make the fail fast mode deterministic
        for requirementCheck in sorted(failed_requirements_checks, key=lambda x: (x.identifier, x.severity)):
            # add only the issues for the current profile when the `target_profile_only` mode is disabled
            # (issues related to other profiles will be added by the corresponding profile validation)
            if requirementCheck.requirement.profile == shacl_context.current_validation_profile or \
                    shacl_context.settings.get("target_only_validation", False):
                for violation in failed_requirements_checks_violations[requirementCheck.identifier]:
                    c = shacl_context.result.add_check_issue(
                        message=violation.get_result_message(shacl_context.rocrate_path),
                        check=requirementCheck,
                        severity=violation.get_result_severity(),
                        resultPath=violation.resultPath.toPython() if violation.resultPath else None,
                        focusNode=make_uris_relative(
                            violation.focusNode.toPython(), shacl_context.publicID),
                        value=violation.value)
                    # if the fail fast mode is enabled, stop the validation after the first issue
                    if shacl_context.fail_fast:
                        break

            # If the fail fast mode is disabled, notify all the validation issues
            # related to profiles other than the current one.
            # They are issues which have not been notified yet because skipped during
            # the validation of their corresponding profile because SHACL checks are executed
            # all together and not profile by profile
            if requirementCheck.identifier not in failed_requirement_checks_notified:
                #
                if requirementCheck.requirement.profile != shacl_context.current_validation_profile:
                    failed_requirement_checks_notified.append(requirementCheck.identifier)
                    shacl_context.result.add_executed_check(requirementCheck, False)
                    shacl_context.validator.notify(RequirementCheckValidationEvent(
                        EventType.REQUIREMENT_CHECK_VALIDATION_END, requirementCheck, validation_result=False))
                    logger.debug("Added validation issue to the context: %s", c)

            # if the fail fast mode is enabled, stop the validation after the first failed check
            if shacl_context.fail_fast:
                break

        # As above, but for skipped checks which are not failed
        logger.debug("Skipped checks: %s", len(shacl_context.result.skipped_checks))
        for requirementCheck in list(shacl_context.result.skipped_checks):
            logger.debug("Processing skipped check: %s", requirementCheck.identifier)
            if not isinstance(requirementCheck, SHACLCheck):
                logger.debug("Skipped check is not a SHACLCheck: %s", requirementCheck.identifier)
                continue
            if requirementCheck.requirement.profile != shacl_context.current_validation_profile and \
                    requirementCheck not in failed_requirements_checks and \
                    requirementCheck.identifier not in failed_requirement_checks_notified:
                failed_requirement_checks_notified.append(requirementCheck.identifier)
                shacl_context.result.add_executed_check(requirementCheck, True)
                shacl_context.validator.notify(RequirementCheckValidationEvent(
                    EventType.REQUIREMENT_CHECK_VALIDATION_END, requirementCheck, validation_result=True))
                logger.debug("Added skipped check to the context: %s", requirementCheck.identifier)

        logger.debug("Remaining skipped checks: %r", len(shacl_context.result.skipped_checks))
        for requirementCheck in shacl_context.result.skipped_checks:
            logger.debug("Remaining skipped check: %r - %s", requirementCheck.identifier, requirementCheck.name)
        end_time = timer()
        logger.debug(f"Execution time for parsing the validation result: {end_time - start_time} seconds")

        return failed_requirements_checks

    @classmethod
    def get_instance(cls, shape: Shape) -> Optional["SHACLCheck"]:
        return cls.__instances__.get(hash(shape), None)

    @classmethod
    def __add_instance__(cls, shape: Shape, check: "SHACLCheck") -> None:
        cls.__instances__[hash(shape)] = check

    @classmethod
    def clear_instances(cls) -> None:
        cls.__instances__.clear()


__all__ = ["SHACLCheck"]
