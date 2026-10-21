.. _validation_examples:

Validation examples
===================

Validate a metadata dictionary
------------------------------

The notebook below lets you compare ``auto``, ``attached``, and ``detached``
using the same metadata dictionary. It also demonstrates metadata-only and
full validation with a local package directory, and displays the report header
and JSON summary for each run.

Read it online or :download:`download the notebook
<validate_metadata_dict_package_modes.ipynb>` to run it locally.

To run the examples:

1. Open the notebook in a notebook editor, such as VS Code or Jupyter, with
   the repository's ``.venv`` Python environment selected as the kernel.
2. Set ``INPUT_PATH`` to your metadata JSON file. For validation with payload
   files, set ``ATTACHED_CRATE_DIR`` to your local crate directory.
3. Choose the target profile and ``OFFLINE`` setting, then run the cells in order.
   External resources may be fetched when ``OFFLINE=False``.

The documentation build does not execute the notebook. See
:doc:`../3_usage_api` for API usage and :ref:`package_modes` for the assumptions
and accepted input combinations.

.. toctree::
   :maxdepth: 1

   validate_metadata_dict_package_modes
