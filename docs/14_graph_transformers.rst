..
   Copyright (c) 2024-2026 CRS4

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

.. _graph-transformers:

Graph transformers
==================

Graph transformers are an internal preprocessing extension point for cases in
which a SHACL shape needs information that is available in the original
RO-Crate graph but would be lost or become ambiguous after an ontology mix-in,
inference, or SHACL rule expansion. They can also add a reusable annotation
which would otherwise have to be recomputed by several expensive SPARQL
targets.

Do not use a transformer for an ordinary validation condition. Prefer SHACL
Core, a SPARQL constraint, or a Python check whenever those can express the
requirement directly. A transformer changes the graph seen by every SHACL
shape, so its output is global to the validation run and requires broader
regression testing.

Why a single SHACL phase is not enough
--------------------------------------

Consider a crate containing a ``schema:PropertyValue`` whose
``schema:propertyID`` points to an identifier scheme. The scheme IRI is a
reference, not an entity described by the crate. The following is a complete
minimal JSON-LD input. The namespace ``https://vocab.example.org/`` is
an arbitrary external vocabulary namespace.

.. code-block:: json

   {
     "@context": {
       "schema": "http://schema.org/",
       "id": "@id",
       "type": "@type",
       "about": { "@id": "schema:about", "@type": "@id" },
       "identifier": { "@id": "schema:identifier", "@type": "@id" },
       "name": "schema:name",
       "propertyID": { "@id": "schema:propertyID", "@type": "@id" },
       "value": "schema:value"
     },
     "@graph": [
       {
         "id": "ro-crate-metadata.json",
         "type": "schema:CreativeWork",
         "about": { "id": "./" }
       },
       {
         "id": "./",
         "type": "schema:Dataset",
         "name": "Example crate",
         "identifier": { "id": "#identifier" }
       },
       {
         "id": "#identifier",
         "type": "schema:PropertyValue",
         "propertyID": {
           "id": "https://vocab.example.org/identifier-scheme"
         },
         "value": "ORCID"
       }
     ]
   }

After JSON-LD expansion, but **before an ontology mix-in, inference, or SHACL
rule expansion**, the relevant part of the RDF graph is:

.. code-block:: turtle

   @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
   @prefix schema: <http://schema.org/> .
   @prefix vocab: <https://vocab.example.org/> .

   <ro-crate-metadata.json>
       rdf:type schema:CreativeWork ;
       schema:about <./> .

   <./>
       rdf:type schema:Dataset ;
       schema:name "Example crate" ;
       schema:identifier <#identifier> .

   <#identifier>
       rdf:type schema:PropertyValue ;
       schema:propertyID vocab:identifier-scheme ;
       schema:value "ORCID" .

At this point ``vocab:identifier-scheme`` occurs only as the object of
``schema:propertyID``. It has no outgoing assertion and is therefore a
cited-only reference. In particular, it is not yet a subject selected by a
target of the form ``?this a ?type``.

A single-phase SHACL implementation can try to classify nodes from the triples
visible at the time of validation. In pySHACL, a ``CONSTRUCT`` query is used as
the body of a ``sh:SPARQLRule`` through ``sh:construct``; it is not the query
form of a ``sh:SPARQLTarget``. The following is a complete shapes-graph
fragment. Its target is deliberately selected only after the ontology makes the
term an ``owl:Class`` instance:

.. code-block:: turtle

   @prefix ex: <https://example.org/> .
   @prefix owl: <http://www.w3.org/2002/07/owl#> .
   @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
   @prefix sh: <http://www.w3.org/ns/shacl#> .

   ex:CandidateMarkerShape
       a sh:NodeShape ;
       sh:targetClass owl:Class ;
       sh:rule [
           a sh:SPARQLRule ;
           sh:construct """
               CONSTRUCT {
                   $this ex:validationCandidate true
               }
               WHERE {
                   $this ?predicate ?object .
                   FILTER(?predicate != rdf:type)
               }
           """
       ] .

This is the same mechanism described in the `pySHACL Inference and Rules
documentation <https://github.com/RDFLib/pySHACL#inference-and-rules>`_ and in
the normative `SHACL-AF SPARQL Rules specification
<https://www.w3.org/TR/shacl-af/#SPARQLRule>`_. It is enabled in pySHACL with
``advanced=True`` (or can be run explicitly with ``shacl_rules(...)``).

On the original Turtle graph, this rule cannot classify
``vocab:identifier-scheme`` from its outgoing assertions because the IRI does
not occur as a subject. The distinction is available at this stage: the IRI is
only the object of ``schema:propertyID``.

Now suppose the validator supplies the following ontology graph, or enables
inference which produces equivalent additional triples:

.. code-block:: turtle

   @prefix owl: <http://www.w3.org/2002/07/owl#> .
   @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
   @prefix vocab: <https://vocab.example.org/> .

   vocab:identifier-scheme
       a owl:Class ;
       rdfs:label "Identifier scheme" .

The ontology mix-in adds these ontology triples to the data graph before pySHACL
applies SHACL rules. With OWL-RL inference, further triples such as
the following can also be present:

.. code-block:: turtle

   vocab:identifier-scheme
       <http://www.w3.org/2002/07/owl#sameAs>
           vocab:identifier-scheme .

The term is now a subject with a type and with outgoing predicates that were
not asserted by the crate. The same single-phase rule now sees the injected
``rdfs:label`` or inferred ``owl:sameAs`` and marks
``vocab:identifier-scheme`` as a validation candidate. It cannot distinguish
those generated statements from assertions in the crate. The same problem can
occur without an ontology when inference or an earlier SHACL rule expands the
graph.

Changing ``sh:order`` does not solve this problem. SHACL rule ordering applies
after the ontology mix-in and pre-inference, so it cannot restore the
provenance that was present in the first Turtle graph. The required operation
is two-phase: classify nodes using the original graph, then validate a copy of
that graph after normal ontology and inference expansion. The graph transformer
pipeline implements that separation; the private candidate marker added to
the transient copy is not inferred from ontology triples.

How the pipeline works
----------------------

``prepare_data_graph`` creates one transient copy of the parsed RO-Crate graph,
discovers all modules below ``rocrate_validator.graph_transformers``, and runs
their registered transformers sequentially. The cached source graph is never
passed to a transformer and remains unchanged.

The validator skips this preprocessing when pySHACL is called with
``sparql_mode=True``. Transformer-dependent validation therefore requires the
normal in-memory or serialized-graph validation mode.

Lower ``order`` values run first. Transformers with the same order are sorted
by their fully qualified Python name, so their order is deterministic but
should not be used to encode an implicit dependency. Assign distinct orders
when one transformer consumes triples produced by another.

Developing transformers
-----------------------

The following sections describe the contract and development workflow for
adding a transformer to the bundled package.

Transformer contract
~~~~~~~~~~~~~~~~~~~~

Every transformer must:

* accept exactly one ``rdflib.Graph``;
* return an ``rdflib.Graph`` (returning ``None`` is an error);
* be deterministic for the same input graph;
* avoid network access and process-global mutable state;
* treat the graph as transient validator state, never as metadata to write back
  to the RO-Crate.

The discovery mechanism covers modules bundled in the
``rocrate_validator.graph_transformers`` package. It is not an entry-point
system for arbitrary profile-local or third-party plugins.

Function transformers
~~~~~~~~~~~~~~~~~~~~~

Use ``@graph_transformer`` for a stateless transformation that is naturally
expressed as a function:

.. code-block:: python

   from rdflib import Graph

   from rocrate_validator.graph_transformers import graph_transformer


   @graph_transformer(order=50)
   def add_example_annotations(data_graph: Graph) -> Graph:
       # Add annotations to the transient graph.
       ...
       return data_graph

The module does not need to be imported manually. It is imported by discovery
the first time ``prepare_data_graph`` runs.

Class transformers
~~~~~~~~~~~~~~~~~~

Use a ``GraphTransformer`` subclass when the implementation benefits from
private helper methods or a clearer class-level contract:

.. code-block:: python

   from rdflib import Graph

   from rocrate_validator.graph_transformers import GraphTransformer


   class ExampleTransformer(GraphTransformer):
       order = 60

       def transform(self, data_graph: Graph) -> Graph:
           ...
           return data_graph

Every concrete subclass is registered automatically. It must have a no-argument
constructor; a new instance is created for each pipeline execution so state
does not leak between validations. Abstract intermediate subclasses are not
registered.

Private marker predicates and prefixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A transformer may annotate the transient graph with private predicates. Keep
these predicates in the validator-owned namespace
``https://github.com/crs4/rocrate-validator/graph-transformers/`` and define
their RDFLib vocabulary terms in ``graph_transformers/vocabulary.py``. These triples
are implementation details: they must not be serialized into an RO-Crate or
presented as vocabulary terms owned by the crate.

When a SHACL query consumes a marker, declare the namespace in the profile's
shared ``sh:prefixes`` block. For example:

.. code-block:: turtle

   sh:declare [
       sh:prefix "validator-transformers" ;
       sh:namespace
           "https://github.com/crs4/rocrate-validator/graph-transformers/"^^xsd:anyURI ;
   ] .

The query can then select only nodes annotated before pySHACL expands the
graph:

.. code-block:: sparql

   FILTER EXISTS {
       ?this validator-transformers:validationCandidate true
   }

Testing a transformer
~~~~~~~~~~~~~~~~~~~~~

Add unit tests for the transformation itself and integration tests for every
SHACL target which consumes its output. At minimum, verify that:

* the source graph is unchanged;
* consecutive transformers see their predecessors' output;
* ordering is explicit when transformers depend on each other;
* ontology and inference triples do not accidentally enter the intended scope;
* representative large graphs remain within the project's performance budget.
