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

.. _api:

###################################################
API documentation
###################################################

This section documents the ``rocrate_validator`` package's API. The
``rocrate_validator`` package provides tools for managing validation profiles,
for using them to validate RO-Crate metadata, and for interpreting the results. Below,
you will find descriptions and usage examples for the core services, models,
and other components provided by the package.
See the :ref:`Index <genindex>` for an alphabetical list of API entries.

The Python API is structured in three main parts.

- **Core Services**: functions for validating RO-Crate metadata and managing profiles.
- **Core Models**: classes representing the main entities used in the validation process.
- **Python Check API**: classes and decorators for defining Python-based validation checks.

Each section includes detailed information about the available functions, classes, and their members.

================
Core Services
================

RO-Crate validation
----------------------------------------------
.. raw:: html
    :file: ./diagrams/core-services.validate.svg

.. autofunction:: rocrate_validator.services.validate


RO-Crate profiles
----------------------------------------------
.. raw:: html
    :file: ./diagrams/core-services.profiles.svg

.. autofunction:: rocrate_validator.services.get_profiles
.. autofunction:: rocrate_validator.services.get_profile


================
Core Models
================

The validator's core is built on the main set of classes shown in the following diagram:

.. raw:: html
    :file: ./diagrams/core-model.svg



RO-Crate
-----------------------------------------
.. autoclass:: rocrate_validator.rocrate.ROCrate
    :members:

Profiles, Requirements, and Checks
-----------------------------------------
.. autoclass:: rocrate_validator.models.Profile
    :members:

.. autoclass:: rocrate_validator.models.Requirement
    :members:
    :special-members:
    :show-inheritance:

.. autoclass:: rocrate_validator.models.RequirementCheck
    :members:

Severity
-----------------------------------------
.. autoenum:: rocrate_validator.models.Severity
    :members:

.. autoclass:: rocrate_validator.models.RequirementLevel
    :members:

.. autoclass:: rocrate_validator.models.LevelCollection
    :members:

Validation
-----------------------------------------
.. autoclass:: rocrate_validator.models.ValidationSettings
    :members:

.. autoclass:: rocrate_validator.models.ValidationContext
    :members:

.. autoclass:: rocrate_validator.models.ValidationResult
    :members:

.. autoclass:: rocrate_validator.models.CheckIssue
    :members:

.. _api-composed-profile-identities:

Composed profile check identities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a validation target uses ``prof:isProfileOf`` without an overlay, an
inherited check keeps the identifier and profile of the source that defines it.
When the target also declares ``validator:isRuleOverlayOf``, the API exposes two
identities for checks reused from the overlaid source:

* the **source identity** identifies the physical implementation and remains
  unchanged; and
* the **effective identity** is the profile and identifier used to report the
  check in the current validation.

For example, if an inherited check from
``example-profile-1.2`` has source identifier
``example-profile-1.2_<suffix>``, an overlay targeting
``example-profile-1.3`` reports it as:

.. code-block:: json

   {
       "identifier": "example-profile-1.3_<suffix>",
       "profile": "example-profile-1.3",
       "source_identifier": "example-profile-1.2_<suffix>",
       "source_profile": "example-profile-1.2"
   }

The ``CheckIssue`` properties ``identifier`` and ``profile_identifier`` return
the effective identity. ``source_profile_identifier`` returns the profile that
physically defines the check. The same distinction is present in
``CheckIssue.to_dict()`` / ``to_json()`` through the ``identifier``,
``profile``, ``source_identifier`` and ``source_profile`` keys.

For a check implementation redefined locally by 1.3, ``source_identifier``
remains the physical identifier assigned to the 1.3 check, while the effective
identifier may reuse the relative suffix of the replaced 1.2 check. This keeps
the logical check stable without mutating either ``RequirementCheck`` object.

``RequirementCheck.identifier`` always refers to the source identity. Code
that needs the context-local overlay identity should use
``ValidationContext.effective_check_identifier(check)`` and
``ValidationContext.effective_check_profile(check)``.

``RequirementCheckValidationEvent`` exposes the same distinction through
``effective_identifier`` / ``effective_profile_identifier`` and
``source_identifier`` / ``source_profile_identifier``.

.. autoclass:: rocrate_validator.events.Event
    :members:

.. autoenum:: rocrate_validator.events.EventType
    :members:

.. autoclass:: rocrate_validator.events.Subscriber
    :members:

Errors
-----------------------------------------
.. automodule:: rocrate_validator.errors
    :members:

======================
Python Check API
======================

Requirement Class
-----------------
.. autoclass:: rocrate_validator.requirements.python.PyRequirement
    :members:

Decorators
----------
.. autofunction:: rocrate_validator.requirements.python.requirement
.. autofunction:: rocrate_validator.requirements.python.check
