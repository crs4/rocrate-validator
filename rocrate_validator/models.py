import json
import logging
import os
from rdflib import Graph, URIRef
from rdflib.term import Node

# set up logging
logger = logging.getLogger(__name__)


# Define SHACL namespace
SHACL_NS = "http://www.w3.org/ns/shacl#"

# Define the rocrate-metadata.json file name
ROCRATE_METADATA_FILE = "ro-crate-metadata.json"


class Shape:

    def __init__(self, shape_node: Node, graph: Graph) -> None:
        # check the input
        assert isinstance(shape_node, Node), "Invalid shape node"
        assert isinstance(graph, Graph), "Invalid graph"

        # store the input
        self._shape_node = shape_node
        self._graph = graph

        # create a graph for the shape
        shape_graph = Graph()
        shape_graph += graph.triples((shape_node, None, None))
        self.shape_graph = shape_graph

        # serialize the graph in json-ld
        shape_json = shape_graph.serialize(format="json-ld")
        shape_obj = json.loads(shape_json)
        self.shape_json = shape_obj[0]

    @property
    def node(self) -> Node:
        return self._shape_node

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def name(self):
        return self.shape_json[f'{SHACL_NS}name'][0]['@value']

    @property
    def description(self):
        return self.shape_json[f'{SHACL_NS}description'][0]['@value']

    @property
    def path(self):
        return self.shape_json[f'{SHACL_NS}path'][0]['@id']

    @property
    def nodeKind(self):
        return self.shape_json[f'{SHACL_NS}nodeKind'][0]['@id']


class Violation:

    def __init__(self, violation_node: Node, graph: Graph) -> None:
        # check the input
        assert isinstance(violation_node, Node), "Invalid violation node"
        assert isinstance(graph, Graph), "Invalid graph"

        # store the input
        self._violation_node = violation_node
        self._graph = graph

        # create a graph for the violation
        violation_graph = Graph()
        violation_graph += graph.triples((violation_node, None, None))
        self.violation_graph = violation_graph

        # serialize the graph in json-ld
        violation_json = violation_graph.serialize(format="json-ld")
        violation_obj = json.loads(violation_json)
        self.violation_json = violation_obj[0]

        # get the source shape
        shapes = list(graph.triples(
            (violation_node, URIRef(f"{SHACL_NS}sourceShape"), None)))
        self.source_shape_node = shapes[0][2]

    @property
    def node(self) -> Node:
        return self._violation_node

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def resultSeverity(self):
        return self.violation_json[f'{SHACL_NS}resultSeverity'][0]['@id']

    @property
    def focusNode(self):
        return self.violation_json[f'{SHACL_NS}focusNode'][0]['@id']

    @property
    def resultPath(self):
        return self.violation_json[f'{SHACL_NS}resultPath'][0]['@id']

    @property
    def value(self):
        value = self.violation_json.get(f'{SHACL_NS}value', None)
        if not value:
            return None
        return value[0]['@id']

    @property
    def resultMessage(self):
        return self.violation_json[f'{SHACL_NS}resultMessage'][0]['@value']

    @property
    def sourceConstraintComponent(self):
        return self.violation_json[f'{SHACL_NS}sourceConstraintComponent'][0]['@id']

    @property
    def sourceShape(self) -> Shape:
        return Shape(self.source_shape_node, self._graph)


class ValidationResult:

    def __init__(self, results_graph: Graph, conforms: bool = None, results_text: str = None) -> None:
        # validate the results graph input
        assert results_graph is not None, "Invalid graph"
        assert isinstance(results_graph, Graph), "Invalid graph type"
        # check if the graph is valid ValidationReport
        assert (None, URIRef(f"{SHACL_NS}conforms"),
                None) in results_graph, "Invalid ValidationReport"
        # store the input properties
        self._conforms = conforms
        self.results_graph = results_graph
        self._text = results_text
        # parse the results graph
        self._violations = self.parse_results_graph(results_graph)
        # initialize the conforms property
        if conforms is not None:
            self._conforms = len(self._violations) == 0
        else:
            assert self._conforms == len(
                self._violations) == 0, "Invalid validation result"

    @staticmethod
    def parse_results_graph(results_graph: Graph):
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
            violation = Violation(violation_node, results_graph)
            violations.append(violation)

        return violations

    @property
    def conforms(self) -> bool:
        return self._conforms

    @property
    def violations(self) -> list:
        return self._violations

    @property
    def text(self) -> str:
        return self._text

    @staticmethod
    def from_serialised_results_graph(file_path: str, format: str = 'turtle'):
        # check the input
        assert format in ['turtle', 'n3', 'nt',
                          'xml', 'rdf', 'json-ld'], "Invalid format"
        assert file_path, "Invalid file path"
        assert os.path.exists(file_path), "File does not exist"
        # Load the graph
        logger.debug("Loading graph from file: %s" % file_path)
        g = Graph()
        g.parse(file_path, format=format)
        logger.debug("Graph loaded from file: %s" % file_path)

        # return the validation result
        return ValidationResult(g)
