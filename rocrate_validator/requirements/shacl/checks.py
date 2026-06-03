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

import json
from timeit import default_timer as timer
from typing import Any, Optional, cast

from rdflib import RDF, BNode, Literal, Namespace

from rocrate_validator.constants import SHACL_NS
from rocrate_validator.errors import ROCrateMetadataNotFoundError
from rocrate_validator.events import EventType
from rocrate_validator.models import (
    LevelCollection,
    Requirement,
    RequirementCheck,
    RequirementCheckValidationEvent,
    RequirementLevel,
    Severity,
    SkipRequirementCheck,
    SourceSnippet,
    ValidationContext,
)
from rocrate_validator.requirements.shacl.models import SHACLNode, Shape, ShapesRegistry
from rocrate_validator.requirements.shacl.utils import build_node_subgraph, make_uris_relative, resolve_parent_shape
from rocrate_validator.requirements.shacl.validator import (
    SHACLValidationAlreadyProcessed,
    SHACLValidationContext,
    SHACLValidationContextManager,
    SHACLValidationSkip,
    SHACLValidator,
    SHACLViolation,
)
from rocrate_validator.utils import log as logging

logger = logging.getLogger(__name__)

_SH = Namespace(SHACL_NS)
_TRUE_LITERALS = (Literal(True), Literal("true", datatype=None))


class SHACLCheck(RequirementCheck):
    """
    A SHACL check for a specific shape property
    """

    # Map shape to requirement check instances
    __instances__: dict[int, "SHACLCheck"] = {}

    def __init__(
        self,
        requirement: Requirement,
        shape: Shape,
        name: Optional[str] = None,
        root: bool = False,
        hidden: Optional[bool] = None,
        level: Optional[RequirementLevel] = None,
    ) -> None:
        self._shape = shape
        self._root = root
        # init the check
        super().__init__(
            requirement,
            (name or shape.name if shape and shape.name else shape.parent.name if shape.parent else None),
            description=(
                shape.description if shape and shape.description else shape.parent.description if shape.parent else None
            ),
            level=level,
            hidden=hidden,
        )
        # store the instance
        SHACLCheck.__add_instance__(shape, self)

        # set the check level
        requirement_level_from_path = self.requirement.requirement_level_from_path
        if requirement_level_from_path:
            declared_level = shape.get_declared_level()
            if declared_level and shape.level.severity != requirement_level_from_path.severity:
                logger.warning(
                    'Mismatch in requirement level for check "%s": '
                    "shape level %s does not match the level from the containing folder %s. "
                    "Consider moving the shape property or removing the severity property.",
                    self.name,
                    shape.level,
                    requirement_level_from_path,
                )
        self._level = level

    @property
    def shape(self) -> Shape:
        return self._shape

    @property
    def root(self) -> bool:
        return self._root

    @property
    def deactivated(self) -> bool:
        if self._deactivated:
            return True
        shape = self._shape
        if shape is None:
            return False
        # Same-profile deactivation (cases B & C): the shape itself carries
        # `sh:deactivated true`, possibly because it was redeclared in an
        # extension profile via override-by-name.
        for value in shape.graph.objects(subject=shape.node, predicate=_SH.deactivated):
            if isinstance(value, Literal) and bool(value.toPython()):
                return True
        # Cross-profile deactivation (case A): a descendant profile may add
        # `<parentShapeIRI> sh:deactivated true` to its own shapes graph,
        # without redeclaring the shape. Scan only profiles that inherit
        # (transitively) from the shape's owning profile, so unrelated
        # profiles loaded in the same process can't influence the result.
        # Validator.__do_validate__ pre-loads the shape graphs.
        from rocrate_validator.models import Profile

        owning_profile = self.requirement.profile
        for profile in Profile.get_descendants(owning_profile):
            try:
                registry = ShapesRegistry.get_instance(profile)
            except Exception:
                continue
            if registry.is_node_deactivated(shape.node):
                return True
        return False

    @property
    def description(self) -> str:
        if self._shape.description:
            return self._shape.description
        if self._shape.parent and self._shape.parent.description:
            return self._shape.parent.description
        return f"Check for {self._shape.name}" if self._shape.name else "SHACL validation check"

    def __compute_requirement_level__(self) -> RequirementLevel:
        declared_level = self._shape.get_declared_level() if self._shape else None
        if declared_level:
            return declared_level
        if self.requirement and self.requirement.requirement_level_from_path:
            return self.requirement.requirement_level_from_path
        # When the shape file lives in the profile root and the NodeShape
        # itself does not declare sh:severity, derive the level from the
        # most severe nested PropertyShape instead of defaulting to REQUIRED.
        derived = self.__derive_level_from_properties__()
        if derived:
            return derived
        return LevelCollection.REQUIRED

    def __derive_level_from_properties__(self) -> Optional[RequirementLevel]:
        properties = getattr(self._shape, "properties", None)
        if not properties:
            return None
        declared_levels = [lvl for lvl in (p.get_declared_level() for p in properties) if lvl]
        if not declared_levels:
            return None
        return max(declared_levels, key=lambda lvl: lvl.severity.value)

    @property
    def level(self) -> RequirementLevel:
        if not self._level:
            self._level = self.__compute_requirement_level__()
        return self._level

    @property
    def severity(self) -> Severity:
        return self.level.severity

    def get_source_snippet(self) -> Optional[SourceSnippet]:
        if self._shape is None:
            return None
        try:
            graph = self._shape.graph
            # build a subgraph containing all the triples related to the shape
            subgraph = build_node_subgraph(graph, self._shape.node)
            # identify the owner of the shape
            owner: SHACLNode = self._shape
            while getattr(owner, "parent", None) is not None:
                owner = cast(SHACLNode, owner.parent)
            # if the shape is not a root shape, include the triples linking the owner to the shape
            if owner is not self._shape:
                shacl = Namespace(SHACL_NS)
                target_predicates = (
                    RDF.type,
                    shacl.targetClass,
                    shacl.targetNode,
                    shacl.targetSubjectsOf,
                    shacl.targetObjectsOf,
                    shacl.target,
                )
                for predicate in target_predicates:
                    for triple in owner.graph.triples((owner.node, predicate, None)):
                        subgraph.add(triple)
                        # follow BNode objects (e.g. sh:target referencing an inline SPARQL target)
                        _, _, obj = triple
                        if isinstance(obj, BNode):
                            subgraph += build_node_subgraph(owner.graph, obj)
                # link the owner to the property so the relationship is preserved in the serialization
                subgraph.add((owner.node, shacl.property, self._shape.node))

            # copy bindings so the serialized snippet uses the same prefix declarations as the source file
            for prefix, namespace in graph.namespaces():
                subgraph.bind(prefix, namespace, replace=True)
            # serialize the subgraph to Turtle format
            code = subgraph.serialize(format="turtle")
        except Exception as e:
            logger.debug("Unable to serialize SHACL shape for check %s: %s", self.identifier, e)
            return None
        # if the code is bytes, decode it to string
        if isinstance(code, bytes):
            code = code.decode("utf-8")
        # use the shape source file as the source path for the snippet if available
        source_path = self.requirement.path if self.requirement else None
        # build the source snippet for the check
        return SourceSnippet(
            language="turtle",
            code=code,
            source_path=source_path,
        )

    def execute_check(self, context: ValidationContext):
        logger.debug("Starting check %s", self)
        try:
            logger.debug(
                "SHACL Validation of profile %s requirement %s started",
                self.requirement.profile.identifier,
                self.identifier,
            )
            with SHACLValidationContextManager(self, context) as ctx:
                # The check is executed only if the profile is the most specific one
                logger.debug(
                    "SHACL Validation of requirement check %s (profile: %s) started",
                    self.requirement.profile.identifier,
                    self.identifier,
                )
                result = self.__do_execute_check__(ctx)
                ctx.current_validation_result = self.identifier not in result
                logger.debug(
                    "SHACL Validation of requirement check %s (profile: %s) finished with result %s",
                    self.requirement.profile.identifier,
                    self.identifier,
                    ctx.current_validation_result,
                )
                return ctx.current_validation_result
        except SHACLValidationAlreadyProcessed:
            logger.debug(
                "SHACL Validation of requirement check %s (profile: %s) already processed",
                self.requirement.identifier,
                self.requirement.profile.identifier,
            )
            # The check belongs to a profile which has already been processed
            # so we can skip the validation and return the specific result for the check
            return self.identifier not in [i.check.identifier for i in context.result.get_issues()]
        except SHACLValidationSkip as e:
            logger.debug(
                "SHACL Validation of profile %s requirement %s skipped",
                self.requirement.profile.identifier,
                self.identifier,
            )
            # The validation is postponed to the more specific profiles
            # so the check is not considered as failed.
            raise SkipRequirementCheck(self, str(e)) from e
        except ROCrateMetadataNotFoundError as e:
            logger.debug(
                "Unable to perform metadata validation due to missing metadata file: %s",
                e,
            )
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
            logger.debug(
                "Unable to perform metadata validation " "due to one or more errors in the JSON-LD data file: %s",
                e,
            )
            shacl_context.result.add_issue(
                "Unable to perform metadata validation due to one or more errors in the JSON-LD data file",
                self,
            )
            raise ROCrateMetadataNotFoundError(
                "Unable to perform metadata validation due to one or more errors in the JSON-LD data file"
            ) from e

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
            data_graph=data_graph,
            ontology_graph=ontology_graph,
            **shacl_context.settings.to_dict(),
        )
        # shacl_result.results_graph.serialize("logs/validation_results.ttl", format="turtle")
        # parse the validation result
        end_time = timer()
        logger.debug("Validation '%s' conforms: %s", self.name, shacl_result.conforms)
        logger.debug("Number of violations: %s", len(shacl_result.violations))
        logger.debug(f"Execution time for validating the data graph: {end_time - start_time} seconds")

        # store the validation result in the context
        start_time = timer()
        failed_requirements_checks, failed_requirements_checks_violations = self.__collect_failed_checks__(
            shacl_context, shacl_result, shapes_registry, shapes_graph
        )
        failed_requirement_checks_notified = self.__process_failed_checks__(
            shacl_context, failed_requirements_checks, failed_requirements_checks_violations
        )
        self.__notify_skipped_checks__(shacl_context, failed_requirement_checks_notified)

        logger.debug("Remaining skipped checks: %r", len(shacl_context.result.skipped_checks))
        for skipped_check in shacl_context.result.skipped_checks:
            logger.debug(
                "Remaining skipped check: %r - %s",
                skipped_check.identifier,
                skipped_check.name,
            )
        end_time = timer()
        logger.debug(f"Execution time for parsing the validation result: {end_time - start_time} seconds")

        return failed_requirements_checks

    def __collect_failed_checks__(self, shacl_context, shacl_result, shapes_registry, shapes_graph):
        failed_requirements_checks = set()
        failed_requirements_checks_violations: dict[str, list[SHACLViolation]] = {}
        for violation in shacl_result.violations:
            shape = None
            try:
                shape = shapes_registry.get_shape(Shape.compute_key(shapes_graph, violation.sourceShape))
            except (ValueError, KeyError):
                shape = resolve_parent_shape(shapes_graph, violation.sourceShape, shapes_registry)
                if shape is None:
                    logger.warning(
                        "Unable to map violation to a shape (sourceShape: %s); skipping",
                        violation.sourceShape,
                    )
                    continue
            if shape is None:
                logger.warning(
                    "Shape not found for violation (sourceShape: %s)",
                    violation.sourceShape,
                )
                continue
            requirementCheck = SHACLCheck.get_instance(shape)
            if requirementCheck is None:
                logger.warning("No check instance found for shape: %s", shape.key)
                continue
            # Drop violations whose check severity is below the requested
            # `requirement_severity`: pyshacl still emits sh:ValidationResult
            # nodes for sh:Warning / sh:Info, but they are not actionable at a
            # stricter validation level.
            if requirementCheck.severity < shacl_context.settings.requirement_severity:
                logger.debug(
                    "Dropping violation for check %s: severity %s below requested %s",
                    requirementCheck.identifier,
                    requirementCheck.severity,
                    shacl_context.settings.requirement_severity,
                )
                continue
            if (
                not shacl_context.settings.skip_checks
                or requirementCheck.identifier not in shacl_context.settings.skip_checks
            ):
                failed_requirements_checks.add(requirementCheck)
                violations = failed_requirements_checks_violations.get(requirementCheck.identifier, None)
                if violations is None:
                    failed_requirements_checks_violations[requirementCheck.identifier] = (violations := [])
                violations.append(violation)
        return failed_requirements_checks, failed_requirements_checks_violations

    def __process_failed_checks__(self, shacl_context, failed_requirements_checks,
                                  failed_requirements_checks_violations):
        failed_requirement_checks_notified = [
            _.check.identifier
            for _ in shacl_context.result.get_issues(
                min_severity=cast(Severity, shacl_context.settings.requirement_severity))
        ]
        for requirementCheck in sorted(failed_requirements_checks, key=lambda x: (x.identifier, x.severity)):
            # if the check is not in the current profile
            # and the disable_inherited_profiles_reporting is enabled, skip it
            if (
                requirementCheck.requirement.profile != shacl_context.current_validation_profile
                and shacl_context.settings.disable_inherited_profiles_issue_reporting
            ):
                continue
            for violation in failed_requirements_checks_violations[requirementCheck.identifier]:
                violating_entity = make_uris_relative(cast(Any, violation.focusNode).toPython(),
                                                      shacl_context.publicID)
                violating_property = violation.resultPath.toPython() if violation.resultPath else None
                violation_message = violation.get_result_message(str(shacl_context.rocrate_uri))
                registered_check_issues = shacl_context.result.get_issues_by_check(requirementCheck)
                skip_requirement_check = False
                # check if the violation is already registered
                # and skip the requirement check if it is
                for check_issue in registered_check_issues:
                    if (
                        check_issue.message == violation_message
                        and check_issue.violatingProperty == violating_property
                        and check_issue.violatingEntity == violating_entity
                        and check_issue.violatingPropertyValue == violation.value
                    ):
                        skip_requirement_check = True
                        logger.debug(
                            "Skipping requirement check %s: %s",
                            requirementCheck.identifier,
                            violation_message,
                        )
                        break
                # if the check is not to be skipped, add the issue to the context
                if not skip_requirement_check:
                    c = shacl_context.result.add_issue(
                        message=violation.get_result_message(str(shacl_context.rocrate_uri)),
                        check=requirementCheck,
                        violatingProperty=violating_property,
                        violatingEntity=violating_entity,
                        violatingPropertyValue=violation.value,
                    )
                    logger.debug("Added validation issue to the context: %s", c)
                # if the fail fast mode is enabled, stop the validation after the first issue
                if shacl_context.fail_fast:
                    break

            # If the fail fast mode is disabled, notify all the validation issues
            # related to profiles other than the current one.
            # They are issues which have not been notified yet because skipped during
            # the validation of their corresponding profile because SHACL checks are executed
            # all together and not profile by profile
            if requirementCheck.identifier not in failed_requirement_checks_notified:
                shacl_context.result._add_executed_check(requirementCheck, False)
                if (
                    requirementCheck.identifier not in failed_requirement_checks_notified
                    and requirementCheck.requirement.profile != shacl_context.current_validation_profile
                ):
                    failed_requirement_checks_notified.append(requirementCheck.identifier)
                    shacl_context.validator.notify(
                        RequirementCheckValidationEvent(
                            EventType.REQUIREMENT_CHECK_VALIDATION_END, requirementCheck, validation_result=False
                        )
                    )
                    logger.debug(
                        "Added failed check to the context: %s",
                        requirementCheck.identifier,
                    )

            # if the fail fast mode is enabled, stop the validation after the first failed check
            if shacl_context.fail_fast:
                break
        return failed_requirement_checks_notified

    def __notify_skipped_checks__(self, shacl_context, failed_requirement_checks_notified):
        for skipped_check in list(shacl_context.result.skipped_checks):
            logger.debug("Processing skipped check: %s", skipped_check.identifier)
            if not isinstance(skipped_check, SHACLCheck):
                logger.debug("Skipped check is not a SHACLCheck: %s", skipped_check.identifier)
                continue
            if skipped_check.identifier not in failed_requirement_checks_notified:
                failed_requirement_checks_notified.append(skipped_check.identifier)
                shacl_context.result._add_executed_check(skipped_check, True)
                if (
                    skipped_check.requirement.profile != shacl_context.target_profile
                    and shacl_context.settings.disable_inherited_profiles_issue_reporting
                ):
                    continue
                shacl_context.validator.notify(
                    RequirementCheckValidationEvent(
                        EventType.REQUIREMENT_CHECK_VALIDATION_END,
                        skipped_check,
                        validation_result=True,
                    )
                )
                logger.debug(
                    "Added skipped check to the context: %s",
                    skipped_check.identifier,
                )

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
