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


``ExtraCheck`` Checks
-----------------

``ExtraCheck`` checks are advisory checks that can report suspicious metadata
patterns without affecting whether an RO-Crate conforms to its profile. They
are disabled by default. To run all checks classified as extra_check, pass
``--extra-checks`` to ``validate``:

.. code-block:: console

    rocrate-validator validate <path_to_rocrate> --extra-checks

To omit one extra_check check while running the others, combine this option with
``--skip-checks`` and the check's fully qualified identifier. The validation
report lists extra_check checks and their findings separately from conformance
issues.

.. seealso::

    * To validate without network access and manage the HTTP cache from the
      command line, see :ref:`offline_mode`.
    * For the equivalent Python workflow, see the :doc:`Python API guide
      <3_usage_api>` and the :doc:`API reference <10_api>`.
    * To select additional validation profiles, see
      :doc:`Validation profiles <12_validation_profiles>`; to create a new
      profile, see :doc:`Writing a profile <11_writing_a_profile>`.
    * For choosing Attached/Detached rules, checking only metadata, and
      supported inputs, see :ref:`package_modes`.

Profile detection when ``conformsTo`` is a string
-------------------------------------------------

Profile detection expects JSON-LD references, for example
``"conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"}``. If a
``conformsTo`` value is instead a string, interactive validation can suggest
the matching profile and ask for confirmation before using it. For example,
``"conformsTo": "https://w3id.org/ro/crate/1.2"`` can suggest the
``ro-crate-1.2`` profile even though the value should be an ``{"@id": "..."}``
object. The suggestion is offered only if:

* No ``conformsTo`` value is already a valid entity reference.
* The only problem found during profile detection is that ``conformsTo`` is
  written as a string.
* That URI identifies exactly one available validation profile.

Declining returns to manual profile selection. A warning identifies the affected
metadata entity and shows the correct ``{"@id": "..."}`` form. The metadata is
not changed, so the validation report can still include an error for the
malformed value.

In non-interactive mode, string suggestions are not accepted automatically.
When no usable profile reference is found, validation falls back to the base
``ro-crate`` profile. Specify ``--profile-identifier`` to choose a profile
explicitly, or correct ``conformsTo`` in the metadata descriptor or Root Data
Entity. Use ``--no-auto-profile`` to disable profile detection.

Invalid JSON syntax
-------------------

Profile auto-detection requires syntactically valid JSON. If the metadata
descriptor contains invalid JSON, auto-detection stops and the CLI reports
the parser's reason, line and column, and the affected source line with a
pointer to the error. Correct the JSON syntax and run validation again.
