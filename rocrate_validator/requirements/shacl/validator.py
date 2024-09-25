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

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

import pyshacl
from pyshacl.pytypes import GraphLike
from rdflib import BNode, Graph
from rdflib.term import Node, URIRef

import rocrate_validator.log as logging
from rocrate_validator.models import (Profile, RequirementCheck, Severity,
                                      ValidationContext, ValidationResult)
from rocrate_validator.requirements.shacl.utils import (make_uris_relative,
                                                        map_severity)

from ...constants import (DEFAULT_ONTOLOGY_FILE, RDF_SERIALIZATION_FORMATS,
                          RDF_SERIALIZATION_FORMATS_TYPES, SHACL_NS,
                          VALID_INFERENCE_OPTIONS,
                          VALID_INFERENCE_OPTIONS_TYPES)
from .models import ShapesRegistry

# set up logging
logger = logging.getLogger(__name__)


class SHACLValidationSkip(Exception):
    pass


class SHACLValidationAlreadyProcessed(Exception):

    def __init__(self, profile_identifier: str, result: SHACLValidationResult) -> None:
        super().__init__(f"Profile {profile_identifier} has already been processed")
        self.result = result


class SHACLValidationContextManager:

    def __init__(self, check: RequirementCheck, context: ValidationContext) -> None:
        self._check = check
        self._profile = check.requirement.profile
        self._context = context
        self._shacl_context = SHACLValidationContext.get_instance(context)

    def __enter__(self) -> SHACLValidationContext:
        logger.debug("Entering SHACLValidationContextManager")
        if not self._shacl_context.__set_current_validation_profile__(self._profile):
            raise SHACLValidationAlreadyProcessed(
                self._profile.identifier, self._shacl_context.get_validation_result(self._profile))
        logger.debug("Processing profile: %s (id: %s)", self._profile.name,  self._profile.identifier)
        if self._context.settings.get("target_only_validation", False) and \
                self._profile.identifier != self._context.settings.get("profile_identifier", None):
            logger.debug("Skipping validation of profile %s", self._profile.identifier)
            self.context.result.add_skipped_check(self._check)
            raise SHACLValidationSkip(f"Skipping validation of profile {self._profile.identifier}")
        logger.debug("ValidationContext of profile %s initialized", self._profile.identifier)
        return self._shacl_context

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._shacl_context.__unset_current_validation_profile__()
        logger.debug("Exiting SHACLValidationContextManager")

    @property
    def context(self) -> ValidationContext:
        return self._context

    @property
    def shacl_context(self) -> SHACLValidationContext:
        return self._shacl_context

    @property
    def check(self) -> RequirementCheck:
        return self._check


class SHACLValidationContext(ValidationContext):

    def __init__(self, context: ValidationContext):
        super().__init__(context.validator, context.settings)
        self._base_context: ValidationContext = context
        # reference to the ontology path
        self._ontology_path: Path = None

        # reference to the contextual ShapeRegistry instance
        self._shapes_registry: ShapesRegistry = ShapesRegistry()

        # processed profiles
        self._processed_profiles: dict[str, bool] = {}

        # reference to the current validation profile
        self._current_validation_profile: Profile = None

        # store the validation result of the current profile
        self._validation_result: SHACLValidationResult = None

        # reference to the contextual ontology graph
        self._ontology_graph: Graph = Graph()

    def __set_current_validation_profile__(self, profile: Profile) -> bool:
        if profile.identifier not in self._processed_profiles:
            # augment the ontology graph with the profile ontology
            ontology_graph = self.__load_ontology_graph__(profile.path)
            if ontology_graph:
                self._ontology_graph += ontology_graph
            # augment the shapes registry with the profile shapes
            profile_registry = ShapesRegistry.get_instance(profile)
            profile_shapes = profile_registry.get_shapes()
            profile_shapes_graph = profile_registry.shapes_graph
            logger.debug("Loaded shapes: %s", profile_shapes)

            # enable overriding of checks
            if self.settings.get("allow_requirement_check_override", True):
                from rocrate_validator.requirements.shacl.requirements import \
                    SHACLRequirement
                for requirement in [_ for _ in profile.requirements if isinstance(_, SHACLRequirement)]:
                    logger.debug("Processing requirement: %s", requirement.name)
                    for check in requirement.get_checks():
                        logger.debug("Processing check: %s", check)
                        if check.overridden and check.requirement.profile != self.target_profile:
                            logger.debug("Overridden check: %s", check)
                            profile_shapes_graph -= check.shape.graph
                            profile_shapes.pop(check.shape.key)

            # add the shapes to the registry
            self._shapes_registry.extend(profile_shapes, profile_shapes_graph)
            # set the current validation profile
            self._current_validation_profile = profile
            # return True if the profile should be processed
            return True
        # return False if the profile has already been processed
        return False

    def __unset_current_validation_profile__(self) -> None:
        self._current_validation_profile = None

    @property
    def base_context(self) -> ValidationContext:
        return self._base_context

    @property
    def current_validation_profile(self) -> Profile:
        return self._current_validation_profile

    @property
    def current_validation_result(self) -> SHACLValidationResult:
        return self._validation_result

    @current_validation_result.setter
    def current_validation_result(self, result: ValidationResult):
        assert self._current_validation_profile is not None, "Invalid state: current profile not set"
        # store the validation result
        self._validation_result = result
        # mark the profile as processed and store the result
        self._processed_profiles[self._current_validation_profile.identifier] = result

    def get_validation_result(self, profile: Profile) -> Optional[bool]:
        assert profile is not None, "Invalid profile"
        return self._processed_profiles.get(profile.identifier, None)

    @property
    def result(self) -> ValidationResult:
        return self.base_context.result

    @property
    def shapes_registry(self) -> ShapesRegistry:
        return self._shapes_registry

    @property
    def shapes_graph(self) -> Graph:
        return self.shapes_registry.shapes_graph

    def __get_ontology_path__(self, profile_path: Path, ontology_filename: str = DEFAULT_ONTOLOGY_FILE) -> Path:
        if not self._ontology_path:
            supported_path = f"{profile_path}/{ontology_filename}"
            if self.settings.get("ontology_path", None):
                logger.warning("Detected an ontology path. Custom ontology file is not yet supported."
                               f"Use {supported_path} to provide an ontology for your profile.")
            # overwrite the ontology path if the custom ontology file is provided
            self._ontology_path = Path(supported_path)
        return self._ontology_path

    def __load_ontology_graph__(self, profile_path: Path,
                                ontology_filename: Optional[str] = DEFAULT_ONTOLOGY_FILE) -> Graph:
        # load the graph of ontologies
        ontology_graph = None
        ontology_path = self.__get_ontology_path__(profile_path, ontology_filename)
        if os.path.exists(ontology_path):
            logger.debug("Loading ontologies: %s", ontology_path)
            ontology_graph = Graph()
            ontology_graph.parse(ontology_path, format="ttl",
                                 publicID=self.publicID)
            logger.debug("Ontologies loaded: %s", ontology_graph)
        return ontology_graph

    @property
    def ontology_graph(self) -> Graph:
        return self._ontology_graph

    @classmethod
    def get_instance(cls, context: ValidationContext) -> SHACLValidationContext:
        instance = getattr(context, "_shacl_validation_context", None)
        if not instance:
            instance = SHACLValidationContext(context)
            setattr(context, "_shacl_validation_context", instance)
        return instance


class SHACLViolation:

    def __init__(self, result: ValidationResult, violation_node: Node, graph: Graph) -> None:
        # check the input
        assert result is not None, "Invalid result"
        assert isinstance(violation_node, Node), "Invalid violation node"
        assert isinstance(graph, Graph), "Invalid graph"

        # store the input
        self._result = result
        self._violation_node = violation_node
        self._graph = graph

        # initialize the properties for lazy loading
        self._focus_node = None
        self._result_message = None
        self._result_path = None
        self._severity = None
        self._source_constraint_component = None
        self._source_shape = None
        self._source_shape_node = None
        self._value = None

    @property
    def node(self) -> Node:
        return self._violation_node

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def focusNode(self) -> Node:
        if not self._focus_node:
            self._focus_node = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}focusNode"))
            assert self._focus_node is not None, f"Unable to get focus node from violation node {self._violation_node}"
        return self._focus_node

    @property
    def resultPath(self):
        if not self._result_path:
            self._result_path = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}resultPath"))
        return self._result_path

    @property
    def value(self):
        if not self._value:
            self._value = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}value"))
        return self._value

    def get_result_severity(self) -> Severity:
        if not self._severity:
            severity = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}resultSeverity"))
            assert severity is not None, f"Unable to get severity from violation node {self._violation_node}"
            # we need to map the SHACL severity term to our Severity enum values
            self._severity = map_severity(severity.toPython())
        return self._severity

    @property
    def sourceConstraintComponent(self):
        if not self._source_constraint_component:
            self._source_constraint_component = self.graph.value(
                self._violation_node, URIRef(f"{SHACL_NS}sourceConstraintComponent"))
            assert self._source_constraint_component is not None, \
                f"Unable to get source constraint component from violation node {self._violation_node}"
        return self._source_constraint_component

    def get_result_message(self, ro_crate_path: Union[Path, str]) -> str:
        if not self._result_message:
            message = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}resultMessage"))
            assert message is not None, f"Unable to get result message from violation node {self._violation_node}"
            self._result_message = make_uris_relative(message.toPython(), ro_crate_path)
        return self._result_message

    @property
    def sourceShape(self) -> Union[URIRef, BNode]:
        if not self._source_shape_node:
            self._source_shape_node = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}sourceShape"))
            assert self._source_shape_node is not None, \
                f"Unable to get source shape node from violation node {self._violation_node}"
        return self._source_shape_node


class SHACLValidationResult:

    def __init__(self, results_graph: Graph,
                 results_text: str = None) -> None:
        # validate the results graph input
        assert results_graph is not None, "Invalid graph"
        assert isinstance(results_graph, Graph), "Invalid graph type"
        # check if the graph is valid ValidationReport
        assert (None, URIRef(f"{SHACL_NS}conforms"),
                None) in results_graph, "Invalid ValidationReport"
        # store the input properties
        self.results_graph = results_graph
        self._text = results_text
        # parse the results graph
        self._violations = self._parse_results_graph(results_graph)
        # initialize the conforms property
        self._conforms = len(self._violations) == 0

        logger.debug("Validation report. N. violations: %s, Conforms: %s; Text: %s",
                     len(self._violations), self._conforms, self._text)

    def _parse_results_graph(self, results_graph: Graph):
        # parse the violations from the results graph
        violations = []
        for violation_node in results_graph.subjects(predicate=URIRef(f"{SHACL_NS}resultMessage")):
            violation = SHACLViolation(self, violation_node, results_graph)
            violations.append(violation)

        return violations

    @property
    def conforms(self) -> bool:
        return self._conforms

    @property
    def violations(self) -> list[SHACLViolation]:
        return self._violations

    @property
    def text(self) -> str:
        return self._text


class SHACLValidator:

    def __init__(
        self,
        shapes_graph: Optional[Union[GraphLike, str, bytes]],
        ont_graph: Optional[Union[GraphLike, str, bytes]] = None,
    ) -> None:
        """
        Create a new SHACLValidator instance.

        :param shacl_graph: rdflib.Graph or file path or web url
                of the SHACL Shapes graph to use to
        validate the data graph
        :type shacl_graph: rdflib.Graph | str | bytes
        :param ont_graph: rdflib.Graph or file path or web url
                of an extra ontology document to mix into the data graph
        :type ont_graph: rdflib.Graph | str | bytes
        """
        self._shapes_graph = shapes_graph
        self._ont_graph = ont_graph

    @property
    def shapes_graph(self) -> Optional[Union[GraphLike, str, bytes]]:
        return self._shapes_graph

    @property
    def ont_graph(self) -> Optional[Union[GraphLike, str, bytes]]:
        return self._ont_graph

    def validate(
        self,
        # data to validate
        data_graph: Union[GraphLike, str, bytes],
        # validation settings
        abort_on_first: Optional[bool] = True,
        advanced: Optional[bool] = True,
        inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None,
        inplace: Optional[bool] = False,
        meta_shacl: bool = False,
        iterate_rules: bool = True,
        # SHACL validation severity
        allow_infos: Optional[bool] = False,
        allow_warnings: Optional[bool] = False,
        # serialization settings
        serialization_output_path: Optional[str] = None,
        serialization_output_format:
            Optional[RDF_SERIALIZATION_FORMATS_TYPES] = "turtle",
        **kwargs,
    ) -> SHACLValidationResult:
        f"""
        Validate a data graph using SHACL shapes as constraints

        :param data_graph: rdflib.Graph or file path or web url
                of the data to validate
        :type data_graph: rdflib.Graph | str | bytes
        :param advanced: Enable advanced SHACL features, default=False
        :type advanced: bool | None
        :param inference: One of {VALID_INFERENCE_OPTIONS}
        :type inference: str | None
        :param inplace: If this is enabled, do not clone the datagraph,
                manipulate it inplace
        :type inplace: bool
        :param abort_on_first: Stop evaluating constraints after first
                violation is found
        :type abort_on_first: bool | None
        :param allow_infos: Shapes marked with severity of sh:Info
                will not cause result to be invalid.
        :type allow_infos: bool | None
        :param allow_warnings: Shapes marked with severity of sh:Warning
                or sh:Info will not cause result to be invalid.
        :type allow_warnings: bool | None
        :param serialization_output_format: Literal[
            {RDF_SERIALIZATION_FORMATS}
        ]
        :param kwargs: Additional keyword arguments to pass to pyshacl.validate
        """

        # Validate data_graph
        if not isinstance(data_graph, (Graph, str, bytes)):
            raise ValueError(
                "data_graph must be an instance of Graph, str, or bytes")

        # Validate inference
        if inference and inference not in VALID_INFERENCE_OPTIONS:
            raise ValueError(
                f"inference must be one of {VALID_INFERENCE_OPTIONS}")

        # Validate serialization_output_format
        if serialization_output_format and \
                serialization_output_format not in RDF_SERIALIZATION_FORMATS:
            raise ValueError(
                "serialization_output_format must be one of "
                f"{RDF_SERIALIZATION_FORMATS}")

        assert inference in (None, "rdfs", "owlrl", "both"), "Invalid inference option"

        # validate the data graph using pyshacl.validate
        conforms, results_graph, results_text = pyshacl.validate(
            data_graph,
            shacl_graph=self.shapes_graph,
            ont_graph=self.ont_graph,
            inference=inference if inference else "owlrl" if self.ont_graph else None,
            inplace=inplace,
            abort_on_first=abort_on_first,
            allow_infos=allow_infos,
            allow_warnings=allow_warnings,
            meta_shacl=meta_shacl,
            iterate_rules=iterate_rules,
            advanced=advanced,
            js=False,
            debug=False,
            **kwargs,
        )
        # log the validation results
        logger.debug("pyshacl.validate result: Conforms: %r", conforms)
        logger.debug("pyshacl.validate result: Results Graph: %r", results_graph)
        logger.debug("pyshacl.validate result: Results Text: %r", results_text)

        # serialize the results graph
        if serialization_output_path:
            assert serialization_output_format in [
                "turtle",
                "n3",
                "nt",
                "xml",
                "rdf",
                "json-ld",
            ], "Invalid serialization output format"
            results_graph.serialize(
                serialization_output_path, format=serialization_output_format
            )
        # return the validation result
        return SHACLValidationResult(results_graph, results_text)


__all__ = ["SHACLValidator", "SHACLValidationResult", "SHACLViolation"]
