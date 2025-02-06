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

    * Note: some profiles split the checks into folders called ``must/``, 
      ``should/`` and ``may/`` according to the requirement severity. This 
      is not mandatory - you can also label individual checks/shapes with 
      ``sh:severity`` in the SHACL code instead.

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

Running validator & tests during profile development
----------------------------------------------------

To run the test suite, run ``pytest``. New tests should be picked up automatically for 
the new profile.

When running the validator manually, use ``--profile-identifier`` to select the desired profile.

The crates in ``tests/data/crates``` can be used as examples for running the validator. For example: ::

    rocrate-validator validate --profile-identifier your-profile-name tests/data/crates/invalid/1_wroc_crate/no_mainentity/
