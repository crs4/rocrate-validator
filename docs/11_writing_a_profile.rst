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

For guidance on SHACL Core targets, SPARQL target performance, inference and
rule ordering, see :ref:`efficient-shacl-targets`.

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

Writing validation checks
-------------------------

A validation profile can contain two kinds of executable checks. SHACL checks
describe constraints over the crate's RDF graph; Python checks implement
procedural logic for cases that are not conveniently expressed in SHACL. Both
types can be assigned a severity and can participate in profile inheritance,
overrides, overlays and deactivation.

SHACL checks
^^^^^^^^^^^^

A SHACL ``NodeShape`` or ``PropertyShape`` becomes a validation check. Its
``sh:name`` is the human-readable check name used when matching an inherited
check for an override. The shape's target and constraints determine what is
validated; ``sh:severity`` or the profile directory determines its severity.

For example, this shape requires every ``schema:Dataset`` to have a ``name``:

.. code-block:: turtle

   @prefix schema: <http://schema.org/> .
   @prefix sh: <http://www.w3.org/ns/shacl#> .

   <https://example.org/checks/root-name>
       a sh:NodeShape ;
       sh:targetClass schema:Dataset ;
       sh:property [
           sh:path schema:name ;
           sh:name "Root data entity has a name" ;
           sh:minCount 1 ;
           sh:severity sh:Violation ;
       ] .

Python checks
^^^^^^^^^^^^^

Python checks are declared with the ``@check`` decorator in a requirement
module. The decorator's ``name`` and severity identify the check in the same
way as ``sh:name`` and severity identify a SHACL check. The function receives
the validation context and returns the check result or raises a validation
error according to the Python check API.

For example, the following requirement defines a Python check with the same
kind of identity as the SHACL example above:

.. code-block:: python

   from rocrate_validator.models import CheckResult, CheckResultValue, Severity, ValidationContext
   from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

   @requirement(name="Root metadata checks")
   class RootMetadataChecks(PyFunctionCheck):
       @check(name="Root data entity has a name", severity=Severity.REQUIRED)
       def check_name(self, context: ValidationContext) -> CheckResultValue:
           # A check can be skipped before inspecting the crate.
           if context.settings.metadata_only:
               context.record_skip(self, "metadata-only mode", "configured")
               return CheckResult.SKIPPED

           root_entity = context.ro_crate.metadata.get_root_data_entity()
           if root_entity is None:
               # None is normalized to CheckResult.SKIPPED.  Use it when the
               # check has no applicable value to inspect; record_skip() is
               # preferable when the caller can provide a reason.
               return None

           if not root_entity.get_property("name"):
               # A failed check normally records the diagnostic and returns
               # False.  The check framework associates the issue with self.
               context.result.add_issue("The root data entity has no name", self)
               return False

           # True is normalized to CheckResult.PASSED.
           return True

The return annotation is ``CheckResultValue`` because the framework accepts
three equivalent forms: ``True``/``False`` are normalized to passed/failed,
``CheckResult.SKIPPED`` (or the other ``CheckResult`` members) expresses an
explicit status, and ``None`` is normalized to skipped.  When a check fails,
call ``context.result.add_issue(...)`` before returning ``False`` so that the
result contains an actionable diagnostic.  When it is skipped, prefer
``context.record_skip(...)`` when a reason and category should be exposed to
API and CLI consumers.

.. _profile-composition:

Composing validation profiles
-----------------------------

RO-Crate Validator provides four complementary mechanisms for composing the
rules of related profiles:

#. **Ordinary inheritance** applies the checks of a source profile when
   validating against a more specialized target profile.
#. A **check override** replaces one inherited implementation with a local one.
#. A **rule overlay** keeps reusing the source implementations but attributes
   them to the target in validation output.
#. **Deactivation** explicitly suppresses an inherited check.

These mechanisms can be combined, but each answers a different question:
which profiles participate, which implementation runs, how a check is
presented, or whether it runs at all.

The examples below use ``example-profile-1.2`` as source profile ``A`` and
``example-profile-1.3`` as target profile ``B``.

.. container:: profile-composition-table

   .. list-table:: Profile composition mechanisms
      :class: profile-composition-mechanisms
      :header-rows: 1
      :widths: 5 20 30 45

      * - #
        - Mechanism
        - How it is selected
        - Effect
      * - 1
        - Ordinary inheritance
        - ``B prof:isProfileOf A``
        - Applies the rules of both ``A`` and ``B`` while preserving their
          source profiles and identifiers.
      * - 2
        - Check override
        - A check in ``B`` with the same ``(name, severity)`` as a check in
          ``A``
        - Executes the implementation from ``B`` instead of the matching
          implementation from ``A``.
      * - 3
        - Rule overlay
        - ``B prof:isProfileOf A`` plus ``B validator:isRuleOverlayOf A``
        - Presents rules reused from ``A`` with effective profile and
          identifiers based on ``B``, while retaining their source provenance.
      * - 4
        - Deactivation
        - A local deactivation declaration in ``B``
        - Skips the matching inherited check from ``A``.

Replacing a bundled profile through ``--extra-profiles-path`` is not profile
composition: it loads a local profile in place of the predefined profile. See
:doc:`12_validation_profiles` for that separate mechanism.

Ordinary profile inheritance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose that target profile ``B`` declares ``B prof:isProfileOf A``. RO-Crate
Validator interprets this relationship as ordinary profile inheritance: ``B``
is a specialization of ``A`` (in other words, ``B`` *is an* ``A`` in the
validator's conformance model). Consequently, validating a crate against ``B``
means applying both the rules defined by ``B`` and those defined by ``A``. The
validator reuses ``A``'s SHACL and Python checks directly, without copying them
into ``B``'s directory. The reused rules, and therefore their identifiers,
remain attributed to profile ``A``.

In the concrete example, most 1.2 rules still apply to 1.3, so profile 1.3 can
reuse them and define only its new or changed rules. Its ``profile.ttl``
declares the inheritance relationship:

.. code-block:: turtle

   @prefix prof: <http://www.w3.org/ns/dx/prof/> .

   <https://w3id.org/example/profile/1.3>
       a prof:Profile ;
       prof:hasToken "example-profile-1.3" ;
       prof:isProfileOf <https://w3id.org/example/profile/1.2> .

In this example, RO-Crate Validator treats
``example-profile-1.3 prof:isProfileOf example-profile-1.2`` as a validation
dependency. It does **not** copy the 1.2 directory into the 1.3 directory, nor
does it merge their descriptions into a single
:class:`~rocrate_validator.models.profile.Profile` object. When validating
against 1.3, the validator instead:

#. resolves profile 1.2 and any ancestors it declares from the profiles
   available to the current validation session;
#. loads 1.2 requirements from the 1.2 directory and 1.3 requirements from the
   1.3 directory;
#. runs those requirements against the same crate; and
#. keeps each requirement and check linked to the profile and source file that
   defined it.

Consequently, both profile directories must be available to the validator. The
1.3 directory only needs its own ``profile.ttl``, resources and new or changed
checks. Unchanged checks continue to be loaded from the 1.2 directory at
validation time.

For example, suppose 1.2 defines these checks:

* ``Metadata file is valid JSON``;
* ``Root data entity has a name``; and
* ``Root data entity has a license``.

Suppose 1.3 adds a new ``Metadata uses the 1.3 JSON-LD context`` check. With
ordinary inheritance, a validation targeting 1.3 executes:

* the new ``Metadata uses the 1.3 JSON-LD context`` check from 1.3; and
* the unchanged JSON, name and license checks directly from the 1.2 directory.

The new context check and its identifier belong to profile 1.3. The reused
JSON, name and license checks and their identifiers remain attributed to
profile 1.2. No source file is copied and profile 1.2 is not modified.

.. _profile-rule-overlays:

Rule overlays
^^^^^^^^^^^^^

A rule overlay lets a target profile report inherited checks as part of its
own rule set without copying their implementations. It changes the effective
profile and identifiers used in validation output, not which checks are
selected or executed. Profile 1.3 declares 1.2 as both its parent and its
overlay source:

.. code-block:: turtle

   @prefix prof: <http://www.w3.org/ns/dx/prof/> .
   @prefix validator: <https://github.com/crs4/rocrate-validator/> .

   <https://w3id.org/example/profile/1.3>
       a prof:Profile ;
       prof:hasToken "example-profile-1.3" ;
       prof:isProfileOf <https://w3id.org/example/profile/1.2> ;
       validator:isRuleOverlayOf <https://w3id.org/example/profile/1.2> .

.. note::

   ``validator:isRuleOverlayOf`` is an RO-Crate Validator extension, not a
   property defined by the W3C Profiles Vocabulary.


For example, the inherited ``Root data entity has a license`` check is still
implemented by the 1.2 object, but its validation issue and event use 1.3 as
the effective profile. Their source fields continue to identify profile 1.2,
so API consumers can distinguish where a check came from and how it is
reported. The underlying 1.2 object is not mutated. The corresponding result
and event fields are described in :ref:`api-composed-profile-identities`.

When the local 1.3 context check overrides the inherited 1.2 context check, the
overlay also rebases the effective identifier. For example,
``example-profile-1.2_<suffix>`` becomes
``example-profile-1.3_<suffix>`` while the replacement's physical identifier
remains available as its source identifier. This preserves a stable relative
identity across profile versions.

An overlay source must be a direct parent. It does not implicitly overlay that
parent's ancestors.

If a target overlays more than one direct parent, those source profiles must
not define checks with the same ``(name, severity)`` pair. Otherwise, a local
check in the target could match more than one source check and the validator
could not determine which implementation it overrides.

The source and target profiles remain separate: unchanged checks stay in the
source directory, and each check keeps using the ontology and ``sh:prefixes``
resources from the profile that defined it. If a changed 1.3 term mapping
alters a check's meaning, redefine that check locally or provide mappings that
preserve its semantics.

.. note::

   **When to use a rule overlay**

   Use a rule overlay when:

   * the target represents a new version or close variant of the source
     profile;
   * most validation rules are semantically unchanged; and
   * inherited rules should be reported as part of the target profile.

   If reused checks should remain visibly owned by 1.2, use ordinary
   inheritance alone. Do not use an overlay to replace a bundled profile with
   a local copy; use the separate ``--extra-profiles-path`` mechanism
   described in :doc:`12_validation_profiles`.

Overlay validation processes 1.3 checks before checks loaded from 1.2. In the
example, the 1.3 context check can reject incompatible metadata before an
inherited 1.2 check attempts to consume it during fail-fast validation.

Overriding inherited checks
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose 1.2 defines a ``Metadata uses the expected JSON-LD context`` check and
1.3 directly inherits 1.2 through ``prof:isProfileOf``. Profile 1.3 can replace
that check by declaring a local check with the same **name and severity**. This
is a **check override**: the validator executes the 1.3 implementation and
does not execute the matching 1.2 implementation. The mechanism works with
ordinary inheritance as well as rule overlays.

The pair ``(name, severity)`` is the check identity. For example, if the 1.2
context check has ``REQUIRED`` severity but the 1.3 check with the same name
has ``RECOMMENDED`` severity, no override occurs and both checks remain active.
To change severity intentionally, 1.3 must deactivate the original
``REQUIRED`` check and add a distinct ``RECOMMENDED`` check.

An override is resolved against direct parents only. Suppose 1.2 inherits the
context check from a base profile and 1.3 only declares
``1.3 prof:isProfileOf 1.2``. A check declared locally by 1.3 cannot override
that base-profile check. Its defining base profile must also be listed as a
direct parent of 1.3. This restriction keeps override resolution deterministic
in multiple-inheritance hierarchies.

Check override is enabled by default. If the API setting
``allow_requirement_check_override`` is set to ``False``, the matching 1.2 and
1.3 context checks cause an error instead of selecting the 1.3 implementation.

Overriding SHACL checks
~~~~~~~~~~~~~~~~~~~~~~~

Each SHACL ``NodeShape`` / ``PropertyShape`` becomes a check whose name is
its ``sh:name``. To override the inherited 1.2 check, declare a shape in 1.3
with the **same** ``sh:name`` and severity:

.. code-block:: turtle

   # Source profile A (example-profile-1.2)
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

   # Target profile B (example-profile-1.3) -- same sh:name and severity
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
           sh:message "Stricter override from profile 1.3" ;
       ] .

Both top-level shapes and ``PropertyShape`` entries nested inside a parent
``NodeShape`` (i.e., declared inline, without an absolute IRI) can be
overridden this way.

Overriding Python checks
~~~~~~~~~~~~~~~~~~~~~~~~

Python checks declared via the ``@check`` decorator are matched by their
``name`` and severity arguments. To override an inherited 1.2 Python check,
declare a new function with the same identity in profile 1.3:

.. code-block:: python

   # In target profile B's checks module (example-profile-1.3)
   from rocrate_validator.models import CheckResultValue, Severity, ValidationContext
   from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

   @requirement(name="Metadata context checks")
   class MetadataContextChecks(PyFunctionCheck):
       @check(name="Metadata uses the expected JSON-LD context", severity=Severity.REQUIRED)
       def check_context(self, context: ValidationContext) -> CheckResultValue:
           metadata = context.ro_crate.metadata.as_dict()
           actual_context = metadata.get("@context")
           expected_context = "https://w3id.org/ro/crate/1.3/context"
           if actual_context != expected_context:
               context.result.add_issue(
                   f"Expected JSON-LD context {expected_context!r}, got {actual_context!r}",
                   self,
               )
               return False
           return True

The function keeps the inherited check's name and severity, so only its
implementation changes: profile 1.3 accepts the 1.3 context while the 1.2
implementation is not executed.

Rule overlays and check overrides are complementary, not interchangeable. An
overlay determines the effective profile and identifier used for an inherited
check; an override determines which implementation is executed when the target
redefines that check.

Deactivating inherited checks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose a 1.2 check no longer applies to 1.3, rather than merely requiring a
different implementation. Profile 1.3 can **fully deactivate** that inherited
check. The validator then skips it and records it as deactivated in the
validation result. This is useful when 1.3 relaxes a 1.2 expectation or
replaces a coarse-grained 1.2 check with more specific 1.3 checks.

Deactivating SHACL checks
~~~~~~~~~~~~~~~~~~~~~~~~~

Two complementary mechanisms are supported, depending on whether the shape
to disable has an absolute IRI of its own.

**Shape with an absolute IRI** (e.g. a top-level ``NodeShape`` or a named
``PropertyShape``): profile 1.3 references the 1.2 shape by IRI and marks it as
deactivated, without redeclaring it.

.. code-block:: turtle

   # Target profile B (example-profile-1.3)
   <https://w3id.org/example/profile/1.2/ShapeC> sh:deactivated true .

**Nested ``PropertyShape`` without an absolute IRI** (a property declared
inline inside a parent ``NodeShape``): use the check override mechanism
described in the previous section. Declare a new ``PropertyShape`` in the
1.3 profile with the same identity as the one to disable, and set
``sh:deactivated true`` on it. This overrides the 1.2 ``PropertyShape``, and
the validator reports the resulting 1.3 check as deactivated.

.. code-block:: turtle

   # Target profile B (example-profile-1.3) -- disables the inherited check
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

   Profile 1.3 can deactivate the 1.2 shape because it is a descendant of 1.2.
   If an unrelated profile ``C`` declares the same ``sh:deactivated true``
   triple but does not inherit from 1.2, the declaration is ignored. This
   prevents unrelated profiles loaded in the same process from interfering
   with one another.

Deactivating Python checks
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``@check`` decorator accepts a ``deactivated`` flag, mirroring SHACL's
``sh:deactivated``. Combined with check override, profile 1.3 can disable an
inherited 1.2 Python check by redeclaring it with
``deactivated=True``:

.. code-block:: python

   from rocrate_validator.requirements.python import check

   # In target profile B's checks module (example-profile-1.3)
   @check(name="Check Metadata File Descriptor entity existence",
          deactivated=True)
   def disabled(self, ctx):
       # Body is irrelevant — the check is skipped during validation.
       return True

Checking a profile during development
-------------------------------------

Run the profile consistency checks before publishing a new or overlaid
profile:

.. code-block:: bash

   rocrate-validator profiles check example-profile-1.3

The command checks the selected profile and its inherited profiles and reports
each consistency check as ``PASS`` or ``FAIL``. In particular, it detects
duplicate ``(name, severity)`` identities within a profile, invalid or unloaded
overlay sources, and ambiguous identities contributed by multiple overlay
sources. Validation runs perform these profile checks automatically;
``validate --no-profile-checks`` can disable that automatic step when
necessary.

Running validator & tests during profile development
----------------------------------------------------

To run the test suite, run ``pytest``. New tests should be picked up automatically for
the new profile.

When running the validator manually, use ``--profile-identifier`` to select the desired profile.

The crates in ``tests/data/crates``` can be used as examples for running the validator. For example: ::

    rocrate-validator validate \
      --profile-identifier your-profile-name \
      tests/data/crates/invalid/1_wroc_crate/no_mainentity/
