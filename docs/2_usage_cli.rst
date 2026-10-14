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


.. _cli-based-validation:

CLI Validation
==============

.. Include the TOC
.. toctree::
    :maxdepth: 5
    :caption: Getting Started

.. toctree::
    :maxdepth: 5
    :caption: Resources

.. Include the README section for the CLI validation
.. include:: ../README.md
    :parser: myst_parser.sphinx_
    :start-after: ## CLI-based Validation
    :end-before: ## Programmatic Validation


Diagnostic Checks
-----------------

Diagnostic checks are advisory checks that can report suspicious metadata
patterns without affecting whether an RO-Crate conforms to its profile. They
are disabled by default. To run all checks classified as diagnostic, pass
``--include-diagnostic-checks`` to ``validate``:

.. code-block:: console

    rocrate-validator validate <path_to_rocrate> --include-diagnostic-checks

To omit one diagnostic check while running the others, combine this option with
``--skip-checks`` and the check's fully qualified identifier. The validation
report lists diagnostic checks and their findings separately from conformance
issues.

.. seealso::

    * To validate without network access and manage the HTTP cache from the
      command line, see :ref:`offline_mode`.
    * For the equivalent Python workflow, see the :doc:`Python API guide
      <3_usage_api>` and the :doc:`API reference <10_api>`.
    * To select additional validation profiles, see
      :doc:`Validation profiles <12_validation_profiles>`; to create a new
      profile, see :doc:`Writing a profile <11_writing_a_profile>`.
