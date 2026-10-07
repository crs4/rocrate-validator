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


Programmatic Validation
=======================

.. toctree::
    :maxdepth: 5
    :caption: Getting Started

.. toctree::
    :maxdepth: 5
    :caption: Resources

.. include:: ../README.md
    :parser: myst_parser.sphinx_
    :start-after: ## Programmatic Validation
    :end-before: ## Running the tests

.. seealso::

    To resolve resources from a local cache or run validation without network
    access (the ``offline`` / ``no_cache`` settings of ``ValidationSettings``),
    see :ref:`offline_mode`.


Metadata-only Validation
------------------------

In addition to full validation, which checks both metadata and data files,
the library also supports metadata-only validation. This is useful when you
want to ensure that the metadata conforms to the expected schema without
checking the actual data files.

To perform metadata-only validation, you can use the `validate_metadata_as_dict`
from the `rocrate_validator.services` module. This function takes a dictionary
representing the metadata and validates it against a given validation profile.

.. code-block:: python

    import json
    from rocrate_validator.services import validate_metadata_as_dict

    settings = {
        "profile_identifier": "workflow-ro-crate-1.0"
    }

    with open('tests/data/crates/invalid/0_main_workflow/main_workflow_bad_type/ro-crate-metadata.json', 'r') as f:
        # load the metadata from the JSON file
        rocrate_metadata = json.load(f)

        # validate the metadata dictionary
        result = validate_metadata_as_dict(rocrate_metadata, settings=settings)

        # process the validation result as needed
        ...


Warm validation with a reusable Validator
-----------------------------------------

Applications that validate repeatedly against the same profile can keep a
single :class:`rocrate_validator.models.Validator` instance.  The first call
prepares the selected profile chain, requirements, SHACL shapes, and ontology;
later calls reuse that preparation when the profile settings and RDF-base mode
match. Ordinary crates at different locations therefore share one preparation.

.. code-block:: python

    from rocrate_validator.models import ValidationSettings, Validator

    settings = ValidationSettings(
        rocrate_uri="/path/to/default-crate",
        profile_identifier="my-custom-profile",
        extra_profiles_path="/path/to/custom-profiles",
    )
    validator = Validator(settings)

    # Optional: move profile preparation out of the first measured request.
    validator.prepare()

    default_result = validator.validate()  # existing API remains supported
    crate_a_result = validator.validate("/path/to/crate-a")
    crate_b_result = validator.validate("/path/to/crate-b")

The per-call crate argument does not mutate ``settings.rocrate_uri``. Metadata
dictionaries can be supplied with ``validator.validate(metadata_dict=data)``;
``rocrate_uri`` and ``metadata_dict`` are mutually exclusive in one call.

Every call creates a fresh data graph, result, statistics updates, and SHACL
execution context. The same validator serializes overlapping calls because its
subscriber and current-context state are instance-local; use separate validator
instances when validations must run concurrently.

For metadata without an explicit JSON-LD ``@base`` distinct from the crate
public ID, relative IRIs in profile artifacts are compiled against a stable
internal base. Per-run copies of the SHACL and ontology graphs rebase only those
relative terms to the current crate, while structural shape identifiers and the
crate data graph remain unchanged. Metadata whose explicit ``@base`` differs
from its crate public ID causes the validator to keep a separate prepared plan
for that base combination, limiting plan reuse across crate IDs. Validation
behavior is unchanged. After editing profile files in a long-running process,
call
``validator.clear_prepared_profiles()`` or ``validator.prepare(refresh=True)``
before the next validation.


Formatting Validation Results
-----------------------------

Validation results can be rendered using different output formatters provided by
the library. Two formatter types are available: *text* and *JSON*.
Both rely on the ``rich`` Python library and integrate with the
``rocrate_validator.utils.io_helpers.output.console.Console`` class, which extends
``rich.console.Console`` to support custom formatter registration.

To format results, create a ``Console`` instance, register one formatter,
and then print any validation output object (e.g., the full report or the
aggregated statistics).


TextOutputFormatter
~~~~~~~~~~~~~~~~~~~

``TextOutputFormatter`` renders validation reports as human-readable, styled text.
It is typically used for console output, report generation, or writing results
to a file.

.. code-block:: python

    from rocrate_validator.utils.io_helpers.output.console import Console
    from rocrate_validator.utils.io_helpers.output.text import TextOutputFormatter

    console = Console()
    console.register_formatter(TextOutputFormatter())

    # Print the main validation result
    console.print(result)

    # Print aggregated statistics (violations by severity, executed checks, etc.)
    console.print(result.statistics)

    # Write the output to a file
    with open("validation_report.txt", "w") as f:
        file_console = Console(file=f)
        file_console.register_formatter(TextOutputFormatter())
        file_console.print(result.statistics)
        file_console.print(result)


JSONOutputFormatter
~~~~~~~~~~~~~~~~~~~

``JSONOutputFormatter`` produces JSON-structured output, suitable for logging,
programmatic processing, or integration with external tools.

.. code-block:: python

    from rocrate_validator.utils.io_helpers.output.console import Console
    from rocrate_validator.utils.io_helpers.output.json import JSONOutputFormatter

    console = Console()
    console.register_formatter(JSONOutputFormatter())

    # Print the main validation result as JSON
    console.print(result)

    # Print the aggregated statistics
    console.print(result.statistics)

    # Write the output to a file
    with open("validation_report.json", "w") as f:
        file_console = Console(file=f)
        file_console.register_formatter(JSONOutputFormatter())
        file_console.print(result)
