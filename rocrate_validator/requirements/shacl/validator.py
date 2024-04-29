from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union

import pyshacl
from pyshacl.pytypes import GraphLike
from rdflib import Graph
from rdflib.term import Node, URIRef

from rocrate_validator.models import Severity, ValidationResult

from ...constants import (RDF_SERIALIZATION_FORMATS,
                          RDF_SERIALIZATION_FORMATS_TYPES, SHACL_NS,
                          VALID_INFERENCE_OPTIONS,
                          VALID_INFERENCE_OPTIONS_TYPES)
from .models import ViolationShape

# set up logging
logger = logging.getLogger(__name__)


class SHACLViolation:

    def __init__(self, result: ValidationResult, violation_node: Node, graph: Graph) -> None:
        # check the input
        assert isinstance(violation_node, Node), "Invalid violation node"
        assert isinstance(graph, Graph), "Invalid graph"

        # store the input
        self._violation_node = violation_node
        self._graph = graph

        # store the result object
        self._result = result

        # create a graph for the violation
        violation_graph = Graph()
        violation_graph += graph.triples((violation_node, None, None))
        self.violation_graph = violation_graph

        # serialize the graph in json-ld
        violation_obj = json.loads(violation_graph.serialize(format="json-ld"))
        self._violation_json = violation_obj[0]

        # get the source shape
        shapes = list(graph.triples(
            (violation_node, URIRef(f"{SHACL_NS}sourceShape"), None)))
        self.source_shape_node = shapes[0][2]

    def get_result_message(self, ro_crate_path: Union[Path, str]) -> str:
        return self._make_uris_relative(
            self._violation_json[f'{SHACL_NS}resultMessage'][0]['@value'],
            ro_crate_path)

    def get_result_severity(self) -> Severity:
        shacl_severity = self._violation_json[f'{SHACL_NS}resultSeverity'][0]['@id']
        # we need to map the SHACL severity term to our Severity enum values
        if 'http://www.w3.org/ns/shacl#Violation' == shacl_severity:
            return Severity.REQUIRED
        elif 'http://www.w3.org/ns/shacl#Warning' == shacl_severity:
            return Severity.RECOMMENDED
        elif 'http://www.w3.org/ns/shacl#Info' == shacl_severity:
            return Severity.OPTIONAL
        else:
            raise RuntimeError(f"Unrecognized SHACL severity term {shacl_severity}")

    @property
    def node(self) -> Node:
        return self._violation_node

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def focusNode(self):
        return self._violation_json[f'{SHACL_NS}focusNode'][0]['@id']

    @property
    def resultPath(self):
        return self._violation_json[f'{SHACL_NS}resultPath'][0]['@id']

    @property
    def value(self):
            # we need to map the SHACL severity term to our Severity enum values
            self._severity = map_severity(severity.toPython())

    @property
    def sourceConstraintComponent(self):
        return self._violation_json[f'{SHACL_NS}sourceConstraintComponent'][0]['@id']

            self._result_message = make_uris_relative(message.toPython(), ro_crate_path)

    @property
    def description(self):
        return self.sourceShape.description

    @staticmethod
    def _make_uris_relative(text: str, ro_crate_path: Union[Path, str]) -> str:
        # globally replace the string "file://" with "./
        return text.replace(f'file://{ro_crate_path}', '.')


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
        # Query for validation results
        query = """
        SELECT ?subject
        WHERE {{
            ?subject a <{0}ValidationResult> .
        }}
        """.format(SHACL_NS)

        query_results = results_graph.query(query)

        violations = []
        for r in query_results:
            violation_node = r[0]
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
