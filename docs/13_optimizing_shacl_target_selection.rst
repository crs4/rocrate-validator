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

.. _efficient-shacl-targets:

Optimizing SHACL target selection
=================================

During rule expansion, pySHACL re-evaluates the targets of shapes that carry
rules as triples are added to the data graph (see the `SHACL-AF spec`_ for
details). Targets of validation-only shapes are evaluated afterwards, during
validation. A SPARQL target on a rule-bearing shape that is inexpensive on a
small test crate can therefore dominate runtime on a graph with thousands of
entities.

.. _SHACL-AF spec: https://www.w3.org/TR/shacl-af/

Prefer SHACL Core targets such as ``sh:targetClass``, ``sh:targetNode``,
``sh:targetSubjectsOf`` and ``sh:targetObjectsOf`` when they express the
selection directly. An implicit class target is also available when a shape is
itself declared as an ``rdfs:Class``. Use ``sh:SPARQLTarget`` only when focus
nodes depend on a relationship or exclusion that Core targets cannot express.
Benchmark the complete profile either way: inference and iterative rules can
make a Core target process more focus nodes than an equivalent explicit query.

Rules can classify entities for other shapes without a SPARQL target. All rules
are executed before validation begins, so a shape that merely validates the
inferred class needs no ``sh:order``: ordering matters only when one rule
depends on the output of another. Use ``sh:condition`` to restrict which
focus nodes a rule applies to. A validation-only consumer can then use
``sh:targetClass`` after rule expansion instead of paying for a SPARQL target
during the iterative rule phase. If the consuming shape also carries rules,
its target is still re-evaluated during expansion.

Both shapes and rules have a default ``sh:order`` of zero, and rules sharing the
same order run in an unspecified sequence, so never rely on declaration order.
When a rule on shape A produces a type that shape B targets, assign shape A a
lower order than shape B so the type is inferred before B is evaluated. The
same principle applies to rules on the same shape: the producing rule must
precede the consuming one. Producers need a lower order than their consumers:

.. code-block:: turtle

   ex:FindScripts a sh:NodeShape ;
       sh:targetClass schema:SoftwareSourceCode ;
       sh:order -1 ;
       sh:rule [
           a sh:TripleRule ;
           sh:condition [
               a sh:NodeShape ;
               sh:not [ sh:class bioschemas:ComputationalWorkflow ]
           ] ;
           sh:subject sh:this ;
           sh:predicate rdf:type ;
           sh:object ex:Script ;
       ] .

.. note::

   The SPARQL snippets in this section omit prefix boilerplate. A complete
   ``sh:SPARQLTarget`` must make prefixes such as ``rdf:``, ``rdfs:``,
   ``schema:`` and ``ro:`` available either through inline ``PREFIX``
   declarations or through ``sh:prefixes`` and ``sh:declare``. The bundled
   profiles use the latter form.

.. warning::

   A ``sh:condition`` built on ``sh:not`` makes the rule non-monotonic. If
   ``bioschemas:ComputationalWorkflow`` is itself inferred by another rule, the
   rule above runs first and wrongly classifies the workflow as a script.
   Iterative execution does not repair this, because an inferred triple is never
   retracted. Whenever a condition is negative, the rule producing the negated
   type must have a lower order than the rule testing for its absence.

When Core targets cannot express the selection - for example, when focus nodes
depend on a relationship that ``sh:targetObjectsOf`` cannot capture, or when
an exclusion filter is required - a ``sh:SPARQLTarget`` is justified. In that
case, pre-compute expensive subpatterns in a subquery to avoid large
intermediate cross-products. For instance, when a target needs the Root Data
Entity, compute the small set of roots before joining it to entity patterns:

.. code-block:: sparql

   SELECT ?this
   WHERE {
       { SELECT DISTINCT ?root WHERE {
           ?metadatafile schema:about ?root .
           FILTER(STRENDS(STR(?metadatafile), "ro-crate-metadata.json"))
       } }
       ?this a schema:MediaObject .
       FILTER(!STRSTARTS(STR(?this), CONCAT(STR(?root), "#")))
   }

.. note::

   Without the distinct-root subquery, the target would have the following
   form, with the entity and descriptor patterns together in the outer query:

   .. code-block:: sparql

      SELECT ?this
      WHERE {
          ?this a schema:MediaObject .
          ?metadatafile schema:about ?root .
          FILTER(STRENDS(STR(?metadatafile), "ro-crate-metadata.json"))
          FILTER(!STRSTARTS(STR(?this), CONCAT(STR(?root), "#")))
      }

   For example, 500 ``schema:MediaObject`` entities and 250 entities with a
   ``schema:about`` property, only one of which is the metadata descriptor,
   produce 500 x 250, or 125,000, intermediate combinations before the filter
   is applied. By contrast, the optimized query filters and deduplicates the
   roots first, so the outer query processes only 500 combinations. On a
   synthetic 750-triple graph using RDFLib 7.6.0, a local benchmark reduced
   runtime from 13.82-14.58 seconds to 0.08 seconds
   (timings are machine-dependent).
