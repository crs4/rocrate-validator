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


.. _offline_mode:

Offline Mode and HTTP Caching
=============================

To resolve remote resources — JSON-LD ``@context`` documents, profile artifacts
and, optionally, remote RO-Crates — the validator performs HTTP requests. These
requests go through a **persistent HTTP cache**, which makes validation faster
and reproducible and enables an **offline mode** where requests are served
exclusively from the cache.

This page covers how to use offline mode and manage the cache both from the
:ref:`command line <offline_mode_cli>` and through the
:ref:`Python API <offline_mode_api>`.


How caching works
-----------------

Every HTTP-backed resource fetched during validation is stored in a persistent
cache (by default under the user cache directory, shared across runs). On the
first online validation against a profile, the resources it declares are cached
automatically, so a later run can reuse the same cache without any network
access.

Offline mode (``--offline`` / ``offline=True``) forbids network access
altogether: every request must be satisfied by the cache, otherwise the affected
resource is reported as a cache miss. For this reason offline mode requires the
cache to be enabled and cannot be combined with the cache-disabling options.


.. _offline_mode_cli:

Command-line usage
------------------

Offline validation
~~~~~~~~~~~~~~~~~~~

Pass ``--offline`` to the ``validate`` command to forbid any network access:
every HTTP request must then be satisfied by the cache.

.. code-block:: bash

    rocrate-validator validate --offline path/to/ro-crate

Related options:

- ``--cache-path PATH`` — use a specific cache directory. By default a persistent
  directory under the user cache dir is used, so entries are shared across runs.
- ``--cache-max-age SECONDS`` — maximum age of cached entries; ``-1`` (the
  default) means entries never expire.
- ``--no-cache`` / ``-nc`` — disable the cache entirely: every request hits the
  network and nothing is persisted. This flag is **mutually exclusive** with
  ``--offline``, since offline mode needs the cache to serve requests.

Managing the cache
~~~~~~~~~~~~~~~~~~

The ``cache`` subcommand inspects and manages the HTTP cache:

.. code-block:: bash

    # Show the cache location, backend, size and offline status
    rocrate-validator cache info

    # List cached entries (alias: `ls`); filter, sort or emit JSON
    rocrate-validator cache list
    rocrate-validator cache list --url w3id.org --sort size
    rocrate-validator cache list --json

    # Remove every cached entry
    rocrate-validator cache reset --yes

Pre-populating the cache (warm-up)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before going offline you can pre-fetch everything you will need with
``cache warm``:

.. code-block:: bash

    # Warm the resources declared by every installed profile
    rocrate-validator cache warm --all-profiles

    # Warm only specific profiles
    rocrate-validator cache warm -p ro-crate-1.1 -p workflow-ro-crate-1.0

    # Also fetch and cache remote RO-Crates or arbitrary URLs
    rocrate-validator cache warm --crate https://example.org/crate.zip
    rocrate-validator cache warm -u https://w3id.org/ro/crate/1.1/context

When invoked without any source option, ``cache warm`` defaults to warming all
installed profiles. A summary table reports which URLs were cached, skipped or
failed; the command exits with a non-zero status if any URL fails.


.. _offline_mode_api:

Programmatic usage
------------------

The same offline behaviour can be enabled programmatically through
``ValidationSettings``:

.. code-block:: python

    from rocrate_validator import services, models

    settings = services.ValidationSettings(
        rocrate_uri='/path/to/ro-crate',
        profile_identifier='ro-crate-1.1',
        # Serve every HTTP request from the cache; uncached resources fail.
        offline=True,
        # Optional: use a dedicated cache directory (defaults to the user cache).
        # cache_path='/tmp/rocv-cache',
        # Optional: maximum age of cached entries; -1 (default) = never expire.
        # cache_max_age=-1,
    )

    result = services.validate(settings)

The cache-related settings are:

- ``offline`` (``bool``, default ``False``) — when ``True``, HTTP requests are
  served only from the cache; uncached resources raise a cache-miss error.
- ``no_cache`` (``bool``, default ``False``) — disable the cache entirely. It is
  **incompatible** with ``offline=True`` and raises ``ValueError`` if combined.
- ``cache_path`` (``Path``, optional) — cache directory; defaults to the
  persistent user cache so online and offline runs share the same entries.
- ``cache_max_age`` (``int``, optional) — maximum entry age in seconds; ``-1``
  means entries never expire.

When ``offline`` is ``False``, the resources declared by the selected profiles
are warmed up automatically before validation, so that a later offline run
reusing the same cache succeeds without network access. To pre-populate the cache
explicitly (e.g. in a CI pipeline), use the ``rocrate-validator cache warm``
command described in :ref:`offline_mode_cli`.
