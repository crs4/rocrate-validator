import logging

from rdflib import Graph, Namespace
from rdflib.term import Node

from rocrate_validator.constants import RDF_SYNTAX_NS

# set up logging
logger = logging.getLogger(__name__)


def build_node_subgraph(graph: Graph, node: Node) -> Graph:
    shape_graph = Graph()
    shape_graph += graph.triples((node, None, None))

    # add BNodes
    for _, _, o in shape_graph:
        shape_graph += graph.triples((o, None, None))

    # Use the triples method to get all triples that are part of a list
    RDF = Namespace(RDF_SYNTAX_NS)
    first_predicate = RDF.first
    rest_predicate = RDF.rest
    shape_graph += graph.triples((None, first_predicate, None))
    shape_graph += graph.triples((None, rest_predicate, None))
    for _, _, object in shape_graph:
        shape_graph += graph.triples((object, None, None))

    # return the subgraph
    return shape_graph


def inject_attributes(node_graph: Graph,  obj: object) -> object:
    # inject attributes of the shape property
    for node, p, o in node_graph:
        predicate_as_string = p.toPython()
        logger.debug(f"Processing {predicate_as_string} of property graph {node}")
        if predicate_as_string.startswith("http://www.w3.org/ns/shacl#"):
            property_name = predicate_as_string.split("#")[-1]
            setattr(obj, property_name, o.toPython())

    # return the object
    return obj
