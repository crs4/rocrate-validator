Writing a new profile
=====================

This page is about writing a SHACL validation profile for a new or 
existing RO-Crate profile. It does *not* offer guidance on creating the 
RO-Crate profile itself - for that, see the
`RO-Crate page on Profiles <https://www.researchobject.org/ro-crate/profiles#making-an-ro-crate-profile>`_.

Learning SHACL
--------------

The validator profiles are written in SHACL (Shapes Constraint Language), a 
language for validating RDF graphs against a set of conditions. 
To use SHACL effectively, you also need some familiarity with RDF 
(Resource Description Framework), the technology which underpins 
JSON-LD and therefore RO-Crate.

For an RDF introduction, try the `RDF 1.1 Primer <https://www.w3.org/TR/rdf11-primer/>`_ or 
`Introduction to the Principles of Linked Open Data <https://programminghistorian.org/en/lessons/intro-to-linked-data>`_.

This `chapter on SHACL <https://book.validatingrdf.com/bookHtml011.html>`_ 
from the book `Validating RDF Data <https://book.validatingrdf.com>`_
has examples of most of SHACL's features and is a good place 
to start learning. Other chapters in that book may provide an understanding 
of *why* SHACL is our language of choice for this purpose.

For complex validation, you may also need some knowledge of SPARQL, an RDF 
query language. You can learn about SPARQL in the tutorial
`Using SPARQL to access Linked Open Data <https://programminghistorian.org/en/lessons/retired/graph-databases-and-SPARQL>`_.

All these tools are best learned through practice and examples, so when building a 
profile, it's encouraged to use the 
`other profiles <https://github.com/crs4/rocrate-validator/tree/develop/rocrate_validator/profiles>`_
as a point of reference.

Setting up profile files and tests
----------------------------------

These instructions assume you are familiar with code development using Python and Git.

#. `Install the repository from source <https://rocrate-validator.readthedocs.io/en/latest/1_installation/#installation>`_.
#. From the root folder of the repo, create a folder for the profile under 
   `rocrate_validator/profiles <https://github.com/crs4/rocrate-validator/tree/develop/rocrate_validator/profiles>`_.
#. To set up the profile metadata, copy across ``profile.ttl`` from another 
   profile folder to the folder you created 
   (`example <https://github.com/crs4/rocrate-validator/blob/develop/rocrate_validator/profiles/workflow-ro-crate/profile.ttl>`_) 
   & update that metadata to reflect your profile. In particular:

    #. change the token for the profile to a new and unique name, e.g.
       ``prof:hasToken "workflow-ro-crate-linkml"``. This is the name which 
       can be used to select the profile using ``--profile-identifier``
       argument (and should also be the name of the folder).
    #. Ensure the URI of the profile is unique (the first line after the 
       ``@prefix`` statements), to prevent conflation between this profile 
       and any other profile in the package.
    #. If this profile inherits from another profile in the validator 
       (including the base specification), set ``prof:isProfileOf`` / 
       ``prof:isTransitiveProfileOf`` to that profile's URI (which can be found
       in that profile's own ``profile.ttl``).

#. Create a ``profile-name.ttl`` file in the folder you created - this is 
   where you will write the SHACL for the validation. If you have a lot of 
   checks to write, you can create multiple files - the validator will 
   collect them all automatically at runtime. 

   .. note::

      Some profiles split the checks into folders called ``must/``, 
      ``should/`` and ``may/`` according to the requirement severity. This 
      is not mandatory - you can also label individual checks/shapes with 
      ``sh:severity`` in the SHACL code instead.

#. Optionally, associate an ontology graph with the profile by providing 
   an ``ontology.ttl`` file alongside the SHACL files. 
   This graph is merged into the crate's data graph at validation time, 
   allowing you to define formal relationships and additional definitions 
   between profile entities (e.g., using ``rdfs:subClassOf``, 
   ``owl:equivalentClass``, etc.).
   
   .. warning::

      Including an ontology can significantly impact validation times and 
      overall performance, especially for large graphs. Use with caution.

#. From the root folder of the repo, create a test folder for the profile 
   under 
   `tests/integration/profiles <https://github.com/crs4/rocrate-validator/tree/develop/tests/integration/profiles>`_. The name should match the folder you made earlier.
#. Copy the style of other profiles' tests to build up a test suite for the 
   profile. Add any required RO-Crate test data under 
   `tests/data/crates/ <https://github.com/crs4/rocrate-validator/tree/develop/tests/data/crates>`_
   and create corresponding classes in 
   `tests/ro_crates.py <https://github.com/crs4/rocrate-validator/blob/develop/tests/ro_crates.py>`_ 
   which can be used to fetch the data during the tests.
#. When your profile & tests are written, open a pull request to contribute 
   it back to the repository!

Overriding inherited checks
---------------------------

When a profile inherits from another profile (via ``prof:isProfileOf`` /
``prof:isTransitiveProfileOf``), it automatically receives every check
declared by its ancestors. The validator additionally supports
**override-by-name**: a child profile can replace an inherited check by
declaring a new check with the **same name**.

This allows an extension profile to *redefine* the content of an inherited
check — for example, to make a constraint stricter or looser, change its
severity, or, as described in the next section, fully deactivate it.

Override-by-name is enabled by default. It can be disabled via the
``allow_requirement_check_override`` validation setting (CLI / API), which
will raise an error on duplicate check names instead.

SHACL checks
^^^^^^^^^^^^

Each SHACL ``NodeShape`` / ``PropertyShape`` becomes a check whose name is
its ``sh:name``. To override an inherited check, declare a shape in the
extension profile with the **same** ``sh:name`` as the inherited one:

.. code-block:: turtle

   # Parent profile
   ro:ShapeC
       a sh:NodeShape ;
       sh:name "The Shape C" ;
       sh:targetNode ro:ro-crate-metadata.json ;
       sh:property [
           a sh:PropertyShape ;
           sh:name "Check Metadata File Descriptor entity existence" ;
           sh:path rdf:type ;
           sh:minCount 1 ;
           sh:message "Missing entity" ;
       ] .

.. code-block:: turtle

   # Extension profile — overrides the inherited PropertyShape by sh:name
   ro:ShapeC
       a sh:NodeShape ;
       sh:name "The Shape C" ;
       sh:targetNode ro:ro-crate-metadata.json ;
       sh:property [
           a sh:PropertyShape ;
           sh:name "Check Metadata File Descriptor entity existence" ;
           sh:path rdf:type ;
           sh:minCount 1 ;
           sh:maxCount 1 ;
           sh:message "Stricter override from extension profile" ;
       ] .

Both top-level shapes and ``PropertyShape`` entries nested inside a parent
``NodeShape`` (i.e., declared inline, without an absolute IRI) can be
overridden this way.

Python checks
^^^^^^^^^^^^^

Python checks declared via the ``@check`` decorator are matched by their
``name`` argument. To override an inherited Python check, declare a new
function with the same ``name`` in the extension profile:

.. code-block:: python

   # In the extension profile's checks module
   from rocrate_validator.requirements.python import check

   @check(name="Check Metadata File Descriptor entity existence")
   def overridden_check(self, ctx):
       # New implementation that replaces the inherited one
       ...

Deactivating inherited checks
-----------------------------

A child profile can also **fully deactivate** a check inherited from one of
its ancestors. A deactivated check is skipped during validation and
reported as such in the validation result. This is useful when an extension
profile relaxes the parent's expectations, or replaces a coarse-grained
check with a more specific one declared elsewhere in the same profile.

SHACL checks
^^^^^^^^^^^^

Two complementary mechanisms are supported, depending on whether the shape
to disable has an absolute IRI of its own.

**Shape with an absolute IRI** (e.g. a top-level ``NodeShape`` or a named
``PropertyShape``): reference the shape by IRI from the extension profile
and mark it as deactivated, without redeclaring it.

.. code-block:: turtle

   # Extension profile
   <https://parent-profile/ShapeC> sh:deactivated true .

**Nested ``PropertyShape`` without an absolute IRI** (a property declared
inline inside a parent ``NodeShape``): use the override-by-name mechanism
described in the previous section. Declare a new ``PropertyShape`` in the
extension profile with the same ``sh:name`` as the one to disable, and set
``sh:deactivated true`` on it. This overrides the parent's
``PropertyShape``, and the validator reports the resulting check as
deactivated.

.. code-block:: turtle

   # Extension profile — disables the inherited PropertyShape by sh:name
   ro:ShapeC
       a sh:NodeShape ;
       sh:name "The Shape C" ;
       sh:targetNode ro:ro-crate-metadata.json ;
       sh:property [
           a sh:PropertyShape ;
           sh:name "Check Metadata File Descriptor entity existence" ;
           sh:path rdf:type ;
           sh:deactivated true ;
       ] .

.. note::

   Cross-profile deactivation is scoped to the shape's transitive
   descendants: a ``sh:deactivated true`` triple declared by a profile
   that does not inherit (directly or transitively) from the shape's
   owning profile is ignored. This prevents unrelated profiles loaded in
   the same process from interfering with one another.

Python checks
^^^^^^^^^^^^^

The ``@check`` decorator accepts a ``deactivated`` flag, mirroring SHACL's
``sh:deactivated``. Combined with override-by-name, an extension profile
can disable an inherited Python check by redeclaring it with
``deactivated=True``:

.. code-block:: python

   from rocrate_validator.requirements.python import check

   @check(name="Check Metadata File Descriptor entity existence",
          deactivated=True)
   def disabled(self, ctx):
       # Body is irrelevant — the check is skipped during validation.
       return True

Running validator & tests during profile development
----------------------------------------------------

To run the test suite, run ``pytest``. New tests should be picked up automatically for 
the new profile.

When running the validator manually, use ``--profile-identifier`` to select the desired profile.

The crates in ``tests/data/crates``` can be used as examples for running the validator. For example: ::

    rocrate-validator validate \
      --profile-identifier your-profile-name \
      tests/data/crates/invalid/1_wroc_crate/no_mainentity/
