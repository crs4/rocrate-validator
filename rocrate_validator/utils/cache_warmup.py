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
Helpers to populate the HTTP cache with resources referenced by profile
descriptors.

Profiles describe their external resources using the W3C Profiles Vocabulary
(``prof:hasResource`` / ``prof:hasArtifact``). The URLs declared there are the
ones the validator needs to resolve at runtime (JSON-LD contexts, ontologies,
schemas, ...). By discovering them dynamically we can warm the cache so that
subsequent offline runs find every required resource locally.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, List, Optional, Sequence

from rocrate_validator import constants
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import (OFFLINE_CACHE_MISS_STATUS,
                                          HttpRequester)

if TYPE_CHECKING:
    from rocrate_validator.models import Profile, ValidationSettings

# set up logging
logger = logging.getLogger(__name__)

# Guard to prevent multiple warm-up attempts in the same run.
# This is not a thread-safe mechanism.
__profiles_loaded = False


# SPARQL query returning every artifact URL declared in a profile descriptor.
# We intentionally do not filter by role: any resource the profile declares is
# considered a candidate for warm-up (Vocabulary, Constraints, Schema, ...).
_CACHEABLE_URLS_SPARQL = """
PREFIX prof: <http://www.w3.org/ns/dx/prof/>
SELECT DISTINCT ?artifact
WHERE {
    ?profile prof:hasResource ?resource .
    ?resource prof:hasArtifact ?artifact .
}
"""


@dataclass
class WarmUpResult:
    """Outcome of a warm-up operation."""
    url: str
    status: str  # "ok", "skipped", "failed"
    detail: Optional[str] = None


def discover_profile_cacheable_urls(profile: "Profile") -> List[str]:
    """
    Return the list of HTTP(S) URLs declared by ``profile`` as cacheable
    artifacts. Returns an empty list when the profile has no declared
    artifacts or cannot be parsed.
    """
    graph = profile.profile_specification_graph
    if graph is None:
        logger.debug(
            "Profile %s has no specification graph loaded", getattr(profile, "identifier", "?"))
        return []
    urls: List[str] = []
    try:
        for row in graph.query(_CACHEABLE_URLS_SPARQL):
            artifact = row.artifact
            if artifact is None:
                continue
            value = str(artifact)
            if value.lower().startswith(("http://", "https://")) and value not in urls:
                urls.append(value)
    except Exception as e:
        logger.debug("Failed to query cacheable URLs for profile %s: %s",
                     getattr(profile, "identifier", "?"), e)
    return urls


def discover_cacheable_urls_from_profiles(profiles: Iterable["Profile"]) -> List[str]:
    """
    Aggregate cacheable URLs from the given profiles, preserving order and
    removing duplicates.
    """
    seen: set[str] = set()
    result: List[str] = []
    for profile in profiles:
        for url in discover_profile_cacheable_urls(profile):
            if url not in seen:
                seen.add(url)
                result.append(url)
    return result


def warm_up_urls(urls: Sequence[str]) -> List[WarmUpResult]:
    """
    Fetch each URL so that its response is stored in the HTTP cache.

    Already-cached URLs are skipped. Failures (including HTTP errors and
    offline cache misses) are reported but do not raise.
    """
    requester = HttpRequester()
    results: List[WarmUpResult] = []
    offline = bool(getattr(requester, "offline", False))
    for url in urls:
        try:
            if requester.has_cached(url):
                results.append(WarmUpResult(url=url, status="skipped", detail="already cached"))
                continue
            if offline:
                response = requester.get(url)
            else:
                response = requester.fetch_fresh(url)
            status_code = getattr(response, "status_code", None)
            if status_code is None:
                results.append(WarmUpResult(url=url, status="failed", detail="no status code"))
            elif status_code == OFFLINE_CACHE_MISS_STATUS and offline:
                results.append(WarmUpResult(url=url, status="failed", detail="offline cache miss"))
            elif status_code >= 400:
                results.append(WarmUpResult(url=url, status="failed", detail=f"HTTP {status_code}"))
            else:
                results.append(WarmUpResult(url=url, status="ok", detail=f"HTTP {status_code}"))
        except Exception as e:
            logger.debug("Warm-up failed for %s: %s", url, e)
            results.append(WarmUpResult(url=url, status="failed", detail=str(e)))
    return results


def auto_warm_up_for_settings(settings: "ValidationSettings") -> Optional[List[WarmUpResult]]:
    """
    Perform a best-effort synchronous warm-up triggered by
    ``ValidationSettings.__post_init__``.

    The warm-up is skipped when:

    - offline mode is enabled (nothing to fetch from the network);
    - the cache path is not persistent (auto warm-up only makes sense when
      the cache survives the run);
    - the environment variable ``ROCRATE_VALIDATOR_AUTO_WARM`` is set to a
      value disabling the feature (``0``, ``false``, ``no``, ``off``).
    """
    if getattr(settings, "offline", False):
        return None
    if getattr(settings, "cache_path", None) is None:
        return None
    env_value = os.environ.get(constants.AUTO_WARM_ENV_VAR, "1").strip().lower()
    if env_value in {"0", "false", "no", "off"}:
        logger.debug("Auto warm-up disabled via %s=%s", constants.AUTO_WARM_ENV_VAR, env_value)
        return None

    profile_identifier = getattr(settings, "profile_identifier", None)
    if not profile_identifier:
        return None

    profile = _find_profile(profile_identifier, settings)
    if profile is None:
        return None
    urls = discover_profile_cacheable_urls(profile)
    if not urls:
        return None
    requester = HttpRequester()
    urls_to_fetch = [u for u in urls if not requester.has_cached(u)]
    if not urls_to_fetch:
        logger.debug("Auto warm-up: all %d resources already cached for profile %s",
                     len(urls), profile_identifier)
        return []
    results = warm_up_urls(urls_to_fetch)
    ok = sum(1 for r in results if r.status == "ok")
    logger.info("Auto warm-up: pre-loaded %d/%d resources for profile %s",
                ok, len(urls_to_fetch), profile_identifier)
    return results


def _find_profile(identifier, settings) -> Optional["Profile"]:
    """
    Look up a loaded profile by identifier. Accepts either a string or a list
    (the settings sometimes store a list of identifiers).
    """
    # Import here to avoid a circular import with models.py.
    from rocrate_validator.models import Profile
    from rocrate_validator.utils.paths import get_profiles_path

    # Load profiles to ensure the requested one is available and its graph is parsed.
    global __profiles_loaded
    if not __profiles_loaded:
        profiles_path = getattr(settings, "profiles_path", None) or get_profiles_path()
        extra_profiles_path = getattr(settings, "extra_profiles_path", None)
        try:
            Profile.load_profiles(
                profiles_path=profiles_path,
                publicID=None,
                extra_profiles_path=extra_profiles_path,
            )
            __profiles_loaded = True
        except Exception as e:
            logger.debug("Unable to preload profiles for auto warm-up: %s", e)
            return None

    if isinstance(identifier, (list, tuple)):
        if not identifier:
            return None
        identifier = identifier[0]
    try:
        return Profile.get_by_identifier(identifier)
    except Exception:
        # Fall back to scanning all loaded profiles.
        try:
            for profile in Profile.all():
                if getattr(profile, "identifier", None) == identifier:
                    return profile
        except Exception:
            return None
    return None
