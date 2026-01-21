..
    Copyright (c) 2024 CRS4

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
    :start-line: 121
    :end-line: 162


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
