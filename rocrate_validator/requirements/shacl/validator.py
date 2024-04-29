from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import pyshacl
from pyshacl.pytypes import GraphLike
from rdflib import Graph
from rdflib.term import Node, URIRef

from rocrate_validator.models import Severity, ValidationResult
from rocrate_validator.requirements.shacl.utils import (make_uris_relative,
                                                        map_severity)

from ...constants import (RDF_SERIALIZATION_FORMATS,
                          RDF_SERIALIZATION_FORMATS_TYPES, SHACL_NS,
                          VALID_INFERENCE_OPTIONS,
                          VALID_INFERENCE_OPTIONS_TYPES)
from .models import PropertyShape

# set up logging
logger = logging.getLogger(__name__)


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
            self._focus_node = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}sourceShape"))
            assert self._focus_node is not None, f"Unable to get focus node from violation node {self._violation_node}"
        return self._focus_node

    @property
    def resultPath(self):
        if not self._result_path:
            self._result_path = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}resultPath"))
            assert self._result_path is not None, f"Unable to get result path from violation node {self._violation_node}"
        return self._result_path

    @property
    def value(self):
        if not self._value:
            self._value = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}value"))
            assert self._value is not None, f"Unable to get value from violation node {self._violation_node}"
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
            assert self._source_constraint_component is not None, f"Unable to get source constraint component from violation node {self._violation_node}"
        return self._source_constraint_component

    def get_result_message(self, ro_crate_path: Union[Path, str]) -> str:
        if not self._result_message:
            message = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}resultMessage"))
            assert message is not None, f"Unable to get result message from violation node {self._violation_node}"
            self._result_message = make_uris_relative(message.toPython(), ro_crate_path)
        return self._result_message

    @property
    def sourceShape(self) -> PropertyShape:
        if not self._source_shape_node:
            self._source_shape_node = self.graph.value(self._violation_node, URIRef(f"{SHACL_NS}sourceShape"))
            assert self._source_shape_node is not None, f"Unable to get source shape node from violation node {self._violation_node}"
            self._source_shape = PropertyShape(self._source_shape_node, self.graph)
        return self._source_shape


class SHACLValidationResult:

    def __init__(self, results_graph: Graph,
                 conforms: Optional[bool] = None, results_text: str = None) -> None:
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
        if conforms is None:
            self._conforms = len(self._violations) == 0
        else:
            self._conforms = conforms

        logger.debug("Validation report. N. violations: %s, Conforms: %s; Text: %s",
                     len(self._violations), self._conforms, self._text)

        # TODO: why allow setting conforms through an argument if the value is to be
        # computed based on the presence of Violations?
        assert self._conforms == (len(self._violations) == 0), "Invalid validation result"

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
        data_graph: Union[GraphLike, str, bytes],
        advanced: Optional[bool] = False,
        inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None,
        inplace: Optional[bool] = False,
        abort_on_first: Optional[bool] = False,
        allow_infos: Optional[bool] = False,
        allow_warnings: Optional[bool] = False,
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

        # validate the data graph using pyshacl.validate
        conforms, results_graph, results_text = pyshacl.validate(
            data_graph,
            shacl_graph=self.shapes_graph,
            ont_graph=self.ont_graph,
            inference=inference,
            inplace=inplace,
            abort_on_first=abort_on_first,
            allow_infos=allow_infos,
            allow_warnings=allow_warnings,
            meta_shacl=False,
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
        return SHACLValidationResult(results_graph, conforms, results_text)


__all__ = ["SHACLValidator", "SHACLValidationResult", "SHACLViolation"]
