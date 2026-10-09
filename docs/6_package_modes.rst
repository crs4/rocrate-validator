.. _package_modes:

Package modes and validation scope
==================================

RO-Crate metadata describes data files and their context. It can be supplied
as part of a package or as a separate metadata document. The distinction
between Attached and Detached RO-Crates determines which validation rules apply.

An **Attached RO-Crate** has a root directory containing
``ro-crate-metadata.json`` and, optionally, data files. These data files are
called the **payload**. An Attached crate can also refer to resources on the web.

A **Detached RO-Crate** is a metadata document used without a package root
directory. Its Data Entities (files and directories described in the metadata,
excluding the Root Data Entity, which describes the crate as a whole) must be
web-based resources with absolute identifiers. An absolute identifier includes
a URI scheme, as in ``https://example.org/data.csv``; ``data.csv`` is relative.

Package mode and validation scope answer two separate questions:

* **Which rules should be applied?** Use ``--packaging-mode`` to select
  Attached or Detached rules, or let ``auto`` choose from the input.
* **Should data files be checked?** Add ``--metadata-only`` to check only the
  metadata. This keeps the selected mode's metadata rules.

For example, if you have metadata from an Attached crate but cannot share its
data files, use ``--packaging-mode attached --metadata-only``.

In this guide, a **metadata document** means JSON/JSON-LD supplied as a local
file or through a URL. A **dictionary input** means metadata already loaded
into a Python dictionary and supplied through the API. For a dictionary input,
``package_root`` optionally names the local package directory that provides its
payload files.

To try these options with your own metadata dictionary, see the
:ref:`example notebook <validation_examples>`. It compares all three modes
and demonstrates both validation scopes with a local package directory.

Modes and automatic assumptions
-------------------------------

The `RO-Crate specification
<https://www.researchobject.org/ro-crate/specification/1.3/structure.html#types-of-ro-crate>`_
allows software to assume a package mode from its input or process metadata
without selecting a package mode. The validator uses the defaults described
below. These assumptions select the validation rules; they do not establish
the original package type.

The CLI option ``--packaging-mode`` and API setting
``ValidationSettings.packaging_mode`` accept the following values:

.. list-table:: Available modes
   :header-rows: 1
   :class: package-mode-table
   :widths: 20 80

   * - Mode
     - Behaviour
   * - ``auto`` (default)
     - * **Use when** → the input-based assumptions below suit your case.
       * **Effect** → select rules from the input context; a dictionary without
         ``package_root`` is *Unspecified*, while a dictionary with it is
         *Attached*.
   * - ``attached``
     - * **Use when** → you are validating an Attached crate, including a copy
         of its metadata supplied without the data files.
       * **Effect** → apply Attached rules. Data Entities can use relative
         payload paths or absolute identifiers for web-based resources.
   * - ``detached``
     - * **Use when** → you are validating metadata as a Detached crate.
       * **Effect** → apply Detached rules. Data Entities must have absolute
         identifiers and refer to web-based resources.

With ``auto``, the validator makes these assumptions:

* **Directory or ZIP** → *Attached*.
* **Metadata document**, supplied as a local file or URL → *Detached*.
* **Python dictionary without a package directory** → *Unspecified*. Common
  metadata checks run, while checks requiring Attached or Detached rules are
  recorded as skipped.
* **Python dictionary with ``package_root``** → *Attached*. The dictionary
  supplies the metadata graph and the local directory supplies the payload.

Here, *Unspecified* means that no package type was selected. It is a reported
value, not a fourth option for ``--packaging-mode``. For a dictionary without
``package_root``, select ``attached`` or ``detached`` explicitly to enable those
mode-specific checks.

.. note::

   **A metadata document is not necessarily a Detached crate.** It may be a
   copy of the metadata from an Attached crate. In that case, select
   ``--packaging-mode attached --metadata-only`` explicitly. Using
   ``--metadata-only`` alone does not change the automatic choice of Detached.

The automatic choice uses the input format. It does not examine the Root Data
Entity's identifier or determine whether the described data files exist or are
on the web. An Attached package may contain no data files.

What metadata-only changes
--------------------------

``--metadata-only`` (``metadata_only=True`` in the API) skips data-file checks.
It does **not** change the selected package type or relax its metadata rules.
For example, Detached mode still requires absolute Data Entity identifiers:
``data.csv`` does not meet that requirement, even if a base URL could resolve it
to an absolute URL. See the `File Data Entity requirements
<https://www.researchobject.org/ro-crate/specification/1.3/data-entities.html#file-data-entity>`_.

A successful metadata-only result says nothing about whether the data files
are present or valid. For *Unspecified* input, checks specific to Attached or
Detached crates are also skipped. The report lists the skipped checks.

Input compatibility
-------------------

The tables below show which inputs each mode accepts, for each validation
scope. A cell containing Attached, Detached, or Unspecified means validation can
start using that type; it does not mean the crate passes validation.
**Rejected** means you must change the input or settings before validation can
start. Supported BagIt packages (a packaging format that wraps files and
metadata) follow the directory or ZIP rows, depending on how they are supplied.

Full validation requested
~~~~~~~~~~~~~~~~~~~~~~~~~

This table applies to CLI invocations without ``--metadata-only`` and calls to
``services.validate()`` with ``metadata_only=False``.

.. list-table:: Mode used when metadata and data-file checks are requested
   :header-rows: 1
   :class: package-mode-table
   :widths: 28 24 24 24

   * - Input
     - ``auto``
     - ``attached``
     - ``detached``
   * - Local directory
     - Attached
     - Attached
     - Rejected: select a metadata file or URL instead
   * - Local or remote ZIP
     - Attached
     - Attached
     - Rejected: select a metadata file or URL instead
   * - Local ``ro-crate-metadata.json``
     - Detached
     - Attached; parent directory becomes the package root
     - Detached
   * - Other local JSON/JSON-LD document
     - Detached
     - Rejected: supply the package directory/ZIP or its ``ro-crate-metadata.json``
     - Detached
   * - Metadata document supplied through a URL
     - Detached
     - Rejected: supply a package directory/ZIP or use metadata-only validation
     - Detached
   * - ``metadata_dict`` without ``package_root`` (API)
     - Unspecified; only metadata is checked
     - Rejected for full validation; set ``metadata_only=True``
     - Detached; only metadata is checked
   * - ``metadata_dict`` with local ``package_root`` (API)
     - Attached
     - Attached
     - Rejected: a package directory cannot be Detached

Without ``package_root``, a dictionary has no payload backend, so ``auto`` and
``detached`` inputs are automatically limited to metadata-only validation. For
full Attached validation, set ``package_root`` to a local directory containing
the payload files. The dictionary replaces the metadata descriptor: a physical
``ro-crate-metadata.json`` is not required and, if present, is not read.
Metadata checks use the supplied dictionary, including in metadata-only mode.
The report identifies the dictionary as the metadata source and includes the
package root.

When ``metadata_only=True``, ``package_root`` still selects Attached rules, but
checks that read payload files are skipped.

For full Attached validation, supply the package directory or supported archive.
You can also select the local ``ro-crate-metadata.json`` file with
``--packaging-mode attached``; the validator then uses the directory containing
that file as the package root.

Metadata-only validation requested
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This table applies with ``--metadata-only`` or ``metadata_only=True``. Every
accepted combination checks metadata without checking its data files.

.. list-table:: Mode used when only metadata is checked
   :header-rows: 1
   :class: package-mode-table
   :widths: 28 24 24 24

   * - Input
     - ``auto``
     - ``attached``
     - ``detached``
   * - Local directory
     - Attached
     - Attached
     - Rejected: select a metadata file or URL instead
   * - Local or remote ZIP
     - Attached
     - Attached
     - Rejected: select a metadata file or URL instead
   * - Local ``ro-crate-metadata.json``
     - Detached
     - Attached; data files need not be accessible
     - Detached
   * - Other local JSON/JSON-LD document
     - Detached
     - Attached; the input file can have any name
     - Detached
   * - Metadata document supplied through a URL
     - Detached
     - Attached; data files need not be accessible
     - Detached
   * - ``metadata_dict`` without ``package_root`` (API)
     - Unspecified
     - Attached
     - Detached
   * - ``metadata_dict`` with local ``package_root`` (API)
     - Attached
     - Attached
     - Rejected: a package directory cannot be Detached

The name of the input file can differ from the metadata document's identifier
inside the JSON. Allowing any input filename does not relax the rules for that
identifier or for the rest of the metadata.


Examples
--------

Command line
~~~~~~~~~~~~

Validate an Attached package or a Detached document explicitly:

.. code-block:: console

   rocrate-validator validate ./crate --packaging-mode attached
   rocrate-validator validate ./dataset-ro-crate-metadata.json --packaging-mode detached

Validate metadata from an Attached crate without exposing its payload:

.. code-block:: console

   rocrate-validator validate ./metadata.json --packaging-mode attached --metadata-only
   rocrate-validator validate https://example.org/ro-crate-metadata.json --packaging-mode attached --metadata-only

Python API
~~~~~~~~~~

Select Attached rules when submitting metadata from an Attached crate:

.. code-block:: python

   from rocrate_validator import services

   result = services.validate({
       "rocrate_uri": "https://example.org/ro-crate-metadata.json",
       "profile_identifier": "ro-crate-1.3",
       "packaging_mode": "attached",
       "metadata_only": True,
   })

For dictionary-only input, ``validate_metadata_as_dict()`` enables
metadata-only validation for you. To validate a modified dictionary against a
local Attached package's payload, use ``services.validate()`` with
``metadata_dict``, ``package_root``, and ``metadata_only=False``:

.. code-block:: python

   from pathlib import Path
   from rocrate_validator import services
   from rocrate_validator.models.settings import ValidationSettings

   settings = ValidationSettings(
       rocrate_uri=None,
       metadata_dict=metadata,
       package_root=Path("./my-crate"),
       profile_identifier="ro-crate-1.3",
       packaging_mode="attached",
       metadata_only=False,
   )
   result = services.validate(settings)

The directory supplies payload files; ``metadata_dict`` supplies the metadata
being validated. No metadata descriptor is required on disk. If the directory
contains one, it is ignored for this validation.

.. code-block:: python

   import json
   from rocrate_validator import services

   with open("metadata.json", encoding="utf-8") as source:
       metadata = json.load(source)

   result = services.validate_metadata_as_dict(metadata, settings={
       "profile_identifier": "ro-crate-1.3",
       "packaging_mode": "attached",
   })

Omitting ``packaging_mode`` for a dictionary without ``package_root`` leaves
the mode unspecified. Calling ``services.validate()`` with Attached dictionary
input and no ``package_root`` requires ``metadata_only=True`` explicitly.

Reading the reports
-------------------

The reported **RO-Crate package type** tells you which rules were selected:
Attached, Detached, or Unspecified. It does not certify the original package's
type. **Validation scope** tells you whether metadata-only or full validation
was requested. In Python, read the selected type through
``result.context.ro_crate.package_type``.

JSON results include these fields under ``validation_settings``:

.. list-table:: Fields describing the selected mode and scope
   :header-rows: 1
   :class: package-mode-table
   :widths: 35 65

   * - Field
     - Meaning
   * - ``packaging_mode``
     - Requested mode: ``auto``, ``attached``, or ``detached``.
   * - ``package_type``
     - Mode actually used: ``attached``, ``detached``, or ``unspecified``.
   * - ``packaging_mode_explicit``
     - ``true`` if you selected ``attached`` or ``detached``; ``false`` for ``auto``.
   * - ``metadata_only``
     - ``true`` if only metadata is checked, including when the API enables this
       automatically for dictionary-only input.
   * - ``metadata_source``
     - ``dictionary`` when checks use the supplied metadata dictionary; otherwise
       ``package descriptor``.
   * - ``package_root``
     - Local package directory used to access payload files for dictionary input.

The result's ``skipped_check_details`` explains why checks were skipped. Read
those details alongside the issues and validation scope to understand the limits
of the result.
