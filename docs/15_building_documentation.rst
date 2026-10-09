Building and previewing the documentation
=========================================

Install the documentation dependencies
--------------------------------------

From the repository root, install the documentation dependency group into the
project's virtual environment:

.. code-block:: console

   poetry install --with docs

The documentation uses the Shibuya theme, with a custom palette and styles for
both light and dark mode. The ``docs/Makefile`` uses Sphinx from ``.venv`` when
available, otherwise it uses the executable on ``PATH``.

Build HTML
----------

.. code-block:: console

   make -C docs html

Open ``docs/_build/html/index.html`` to read the generated documentation.

Live preview
------------

.. code-block:: console

   make -C docs serve

Open ``http://localhost:8000`` in your browser. The server listens on
``0.0.0.0``, so it is also accessible through the machine's network address.
Changes to documentation sources, configuration, and static files trigger an
automatic rebuild and reload the browser page. Stop the server with ``Ctrl+C``.

To choose a different address or port:

.. code-block:: console

   make -C docs serve SERVE_HOST=127.0.0.1 SERVE_PORT=8080

The preview server uses ``sphinx-autobuild``. You can override its executable
with ``SPHINXAUTO``, and the regular build executable with ``SPHINXBUILD``.
