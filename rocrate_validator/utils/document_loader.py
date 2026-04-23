# Copyright (c) 2024-2026 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
JSON-LD document loader that routes remote ``@context`` resolution through
``HttpRequester``.

``rdflib``'s built-in JSON-LD parser fetches remote contexts via ``urllib``,
which bypasses the HTTP cache managed by this project. Installing the loader
ensures every remote context resolution benefits from the cache and honors
offline mode.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Optional, Tuple

from rdflib.plugins.shared.jsonld import context as jsonld_context
from rdflib.plugins.shared.jsonld import util as jsonld_util

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import (OFFLINE_CACHE_MISS_STATUS,
                                          HttpRequester, OfflineCacheMissError)

logger = logging.getLogger(__name__)

_install_lock = threading.Lock()
_installed = False
_original_source_to_json = jsonld_util.source_to_json


def _patched_source_to_json(source, fragment_id=None, extract_all_scripts=False):
    # Only intercept remote URL strings; let the original handle everything else.
    if isinstance(source, str) and source.lower().startswith(("http://", "https://")):
        try:
            return _fetch_json_ld(source), None
        except OfflineCacheMissError:
            raise
        except Exception as e:
            logger.debug("Custom JSON-LD loader failed for %s: %s; falling back", source, e)
    return _original_source_to_json(source, fragment_id, extract_all_scripts)


def install_document_loader() -> bool:
    """
    Install the custom JSON-LD document loader. Idempotent.

    Returns ``True`` when the loader is active after the call, ``False`` when
    installation raised an unexpected error (which is logged).
    """
    global _installed

    with _install_lock:
        if _installed:
            return True

        try:
            jsonld_util.source_to_json = _patched_source_to_json
            # The context module imports source_to_json at module import time,
            # so it must be patched separately.
            jsonld_context.source_to_json = _patched_source_to_json  # type: ignore[attr-defined]
        except Exception as e:
            logger.error("Failed to install JSON-LD document loader: %s", e)
            return False

        _installed = True
        logger.debug("JSON-LD document loader installed")
        return True


def uninstall_document_loader() -> bool:
    """
    Restore the original JSON-LD document loader. Primarily intended for tests.

    Returns ``True`` when the loader is no longer active after the call,
    ``False`` when uninstallation raised an unexpected error (which is logged).
    """
    global _installed
    with _install_lock:
        if not _installed:
            return True

        try:
            jsonld_util.source_to_json = _original_source_to_json
            jsonld_context.source_to_json = _original_source_to_json  # type: ignore[attr-defined]
        except Exception as e:
            logger.error("Failed to uninstall JSON-LD document loader: %s", e)
            return False

        _installed = False
        return True


def _fetch_json_ld(url: str) -> Any:
    """
    Fetch a JSON-LD document through ``HttpRequester``.

    Raises ``OfflineCacheMissError`` when running offline and the document
    is not available in the cache. Raises ``RuntimeError`` for other
    non-successful responses.
    """
    requester = HttpRequester()
    headers = {"Accept": "application/ld+json, application/json, */*;q=0.1"}
    response = requester.get(url, headers=headers, allow_redirects=True)
    status = getattr(response, "status_code", None)
    if status == OFFLINE_CACHE_MISS_STATUS and getattr(requester, "offline", False):
        raise OfflineCacheMissError(url)
    if status is None or status >= 400:
        raise RuntimeError(f"Unable to retrieve JSON-LD document from {url} (status {status})")
    try:
        return response.json()
    except ValueError:
        return json.loads(response.text)


def resolve_remote_document(url: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Resolve a remote JSON-LD document, returning ``(json, content_type)``.

    Exposed primarily for tests and warm-up routines that need to reuse the
    loader's semantics (offline handling, cache integration) without wiring
    through rdflib.
    """
    data = _fetch_json_ld(url)
    return data, "application/ld+json"
