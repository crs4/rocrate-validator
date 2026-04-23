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

from __future__ import annotations

import atexit
import os
import random
import string
import threading
from typing import Any, Optional

import requests

from rocrate_validator import constants
from rocrate_validator.utils import log as logging

# set up logging
logger = logging.getLogger(__name__)


# HTTP status code used to signal a cache miss in offline mode.
# 504 is what requests_cache uses when only_if_cached is set and
# no cached response is available.
OFFLINE_CACHE_MISS_STATUS = 504


def _log_cache_outcome(method: str, url: str, response, *, offline: bool, forced_refresh: bool = False) -> None:
    """
    Emit a standardized ``CachedHttpRequester: ...`` message describing whether ``url`` was
    served from the HTTP cache or fetched from the remote server.
    """
    from_cache = getattr(response, "from_cache", None)
    status = getattr(response, "status_code", None)

    if offline and status == OFFLINE_CACHE_MISS_STATUS:
        outcome = "not available in HTTP cache (offline cache miss)"
    elif from_cache is True:
        outcome = "served from HTTP cache"
    elif forced_refresh:
        outcome = "fetched from remote (cache refresh)"
    elif from_cache is False:
        outcome = "fetched from remote"
    else:
        # No from_cache attribute: plain requests.Session or offline fallback stub.
        outcome = "fetched from remote (no cache backend)"

    # Emitted at WARNING for now, pending a downgrade to DEBUG once the feature stabilizes.
    logger.debug("CachedHttpRequester: %s %s %s", method, url, outcome)


class OfflineCacheMissError(RuntimeError):
    """Raised when an HTTP resource is not available in the cache while offline."""

    def __init__(self, url: str):
        super().__init__(
            f"Resource '{url}' is not available in the HTTP cache and "
            f"the validator is running in offline mode. Run online once, or use "
            f"`rocrate-validator cache warm` to pre-populate the cache."
        )
        self.url = url


class HttpRequester:
    """
    A singleton class to handle HTTP requests.

    The session is backed by ``requests_cache`` when available. The requester
    supports an offline mode in which only cached responses are served
    (cache misses yield a 504 response instead of hitting the network).
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> HttpRequester:
        if cls._instance is None:
            logger.debug(f"Creating instance of {cls.__name__} with args: {args}, kwargs: {kwargs}")
            with cls._lock:
                if cls._instance is None:
                    logger.debug(f"Creating instance of {cls.__name__}")
                    cls._instance = super(HttpRequester, cls).__new__(cls)
                    atexit.register(cls._instance.__del__)
                    logger.debug(f"Instance created: {cls._instance.__class__.__name__}")
        return cls._instance

    def __init__(self,
                 cache_max_age: int = constants.DEFAULT_HTTP_CACHE_MAX_AGE,
                 cache_path: Optional[str] = None,
                 offline: bool = False,
                 no_cache: bool = False):
        logger.debug(f"Initializing instance of {self.__class__.__name__} {self}")
        # check if the instance is already initialized
        if not hasattr(self, "_initialized"):
            # check if the instance is already initialized
            with self._lock:
                if not getattr(self, "_initialized", False):
                    # set the initialized flag
                    self._initialized = False
                    # store the parameters
                    try:
                        logger.debug(f"Setting cache_max_age to {cache_max_age}")
                        self.cache_max_age = int(cache_max_age)
                    except ValueError:
                        raise TypeError("cache_max_age must be an integer")
                    self.cache_path_prefix = cache_path
                    self.offline = bool(offline)
                    self.no_cache = bool(no_cache)
                    # flag to indicate if the cache is permanent or temporary
                    self.permanent_cache = cache_path is not None
                    # initialize the session
                    self.__initialize_session__(cache_max_age, cache_path)
                    # set the initialized flag
                    self._initialized = True
        else:
            logger.debug(f"Instance of {self} already initialized")

    def __initialize_session__(self, cache_max_age: int, cache_path: Optional[str] = None):
        # initialize the session
        self.session = None
        logger.debug(f"Initializing instance of {self.__class__.__name__}")
        assert not self._initialized, "Session already initialized"
        # check if requests_cache is installed
        # and set up the cached session
        try:
            if not self.no_cache:
                from requests_cache import CachedSession

                # If cache_path is not provided, use the default path prefix
                if not cache_path:
                    # Generate a random path for the cache
                    # to avoid conflicts with other instances
                    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    cache_path = constants.DEFAULT_HTTP_CACHE_PATH_PREFIX + f"_{random_suffix}"
                    logger.debug(f"Using default cache path: {cache_path}")
                else:
                    logger.debug(f"Using provided cache path: {cache_path}")
                    self.permanent_cache = True
                # Negative cache_max_age means "never expire" (as documented in the CLI);
                # offline mode also forces never-expire so stale entries remain usable.
                expire_after = -1 if (self.offline or cache_max_age < 0) else cache_max_age
                # Initialize the session with a cache
                self.session = CachedSession(
                    # Cache name with random suffix
                    cache_name=str(cache_path),
                    expire_after=expire_after,  # Cache expiration time in seconds
                    backend='sqlite',  # Use SQLite backend
                    allowable_methods=('GET',),  # Cache GET
                    allowable_codes=(200, 302, 404)  # Cache responses with these status codes
                )
                # Apply offline policy: only return cached responses.
                if self.offline:
                    try:
                        self.session.settings.only_if_cached = True
                    except AttributeError:
                        # Older requests_cache versions expose the flag on the session directly.
                        setattr(self.session, "only_if_cached", True)
        except ImportError:
            logger.warning("requests_cache is not installed. Using requests instead.")
        except Exception as e:
            logger.error("Error initializing requests_cache: %s", e)

        # if requests_cache is not installed or an error occurred,
        # use requests instead of requests_cache
        # and create a new session
        if not self.session:
            if self.offline:
                logger.warning(
                    "Offline mode requested but requests_cache is not available: "
                    "HTTP requests will be blocked."
                )
                self.session = _OfflineFallbackSession()
            else:
                logger.debug("Cache disabled: using requests instead of requests_cache")
                self.session = requests.Session()

    def __del__(self):
        """
        Destructor to clean up the cache file used by CachedSession.
        """
        logger.debug(f"Deleting instance of {self.__class__.__name__}")
        if hasattr(self, "permanent_cache") and not self.permanent_cache:
            self.cleanup()

    def cleanup(self):
        """
        Remove the SQLite cache file when the cache is marked as temporary.
        """
        logger.debug(f"Deleting instance of {self.__class__.__name__}")
        if self.session and hasattr(self.session, 'cache') and self.session.cache:
            try:
                logger.debug(f"Deleting cache directory: {self.session.cache.cache_name}")
                cache_path = f"{self.session.cache.cache_name}.sqlite"
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    logger.debug(f"Deleted cache directory: {cache_path}")
            except Exception as e:
                logger.error(f"Error deleting cache directory: {e}")

    def __getattr__(self, name):
        """
        Delegate HTTP methods to the session object, wrapping the call with
        cache-outcome logging.

        :param name: The name of the method to call.
        :return: A callable that proxies to the session method.
        """
        if name.upper() in {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"}:
            method = name.lower()
            session_method = getattr(self.session, method)

            def _wrapped(url, *args, **kwargs):
                response = session_method(url, *args, **kwargs)
                _log_cache_outcome(method.upper(), url, response, offline=self.offline)
                return response

            return _wrapped
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def fetch_fresh(self, url: str, **kwargs) -> requests.Response:
        """
        Fetch ``url`` bypassing the HTTP cache and store the fresh response.

        Used for resources that must always reflect the current remote state
        while still being available offline afterwards (e.g., a remote RO-Crate
        whose cached copy must be refreshed on every online run).

        In offline mode, the cache is consulted as usual (no network traffic).

        :param url: The URL to fetch.
        :return: The HTTP response.
        """
        if self.offline:
            response = self.session.get(url, **kwargs)
        else:
            # ``force_refresh=True`` tells requests_cache to bypass the cache
            # entirely and overwrite the stored entry with the new response.
            # Older requests_cache versions only understand ``refresh=True``
            # (revalidation), and plain ``requests.Session`` accepts neither.
            response = None
            for flag in ("force_refresh", "refresh"):
                try:
                    response = self.session.get(url, **{flag: True}, **kwargs)
                    break
                except TypeError:
                    continue
            if response is None:
                response = self.session.get(url, **kwargs)
        _log_cache_outcome("GET", url, response, offline=self.offline, forced_refresh=not self.offline)
        return response

    def has_cached(self, url: str) -> bool:
        """
        Check whether ``url`` is already present in the HTTP cache.

        Returns ``False`` when the underlying session does not implement a cache.
        """
        cache = getattr(self.session, "cache", None)
        if cache is None:
            return False
        contains = getattr(cache, "contains", None)
        try:
            if contains is not None:
                return bool(contains(url=url))
            # Fallback for older requests_cache versions.
            return bool(cache.has_url(url))
        except Exception as e:
            logger.debug("Cache lookup failed for %s: %s", url, e)
            return False

    def clear_cache(self) -> None:
        """
        Remove every entry from the HTTP cache.
        """
        cache = getattr(self.session, "cache", None)
        if cache is None:
            logger.debug("No cache backend to clear")
            return
        try:
            cache.clear()
            logger.info("HTTP cache cleared")
        except Exception as e:
            logger.error("Failed to clear HTTP cache: %s", e)
            raise

    def cache_info(self) -> dict[str, Any]:
        """
        Return metadata about the current HTTP cache backend.
        """
        info: dict[str, Any] = {
            "backend": None,
            "path": None,
            "permanent": getattr(self, "permanent_cache", False),
            "offline": getattr(self, "offline", False),
            "entries": 0,
            "size_bytes": 0,
        }
        cache = getattr(self.session, "cache", None)
        if cache is None:
            return info
        info["backend"] = cache.__class__.__name__
        cache_name = getattr(cache, "cache_name", None) or getattr(cache, "db_path", None)
        if cache_name:
            info["path"] = f"{cache_name}.sqlite" if not str(cache_name).endswith(".sqlite") else str(cache_name)
        try:
            info["entries"] = len(cache.responses)
        except Exception:
            try:
                info["entries"] = sum(1 for _ in cache.urls())
            except Exception as e:
                logger.debug("Unable to count cache entries: %s", e)
        if info["path"] and os.path.exists(info["path"]):
            try:
                info["size_bytes"] = os.path.getsize(info["path"])
            except OSError:
                pass
        return info

    @classmethod
    def initialize_cache(cls,
                         cache_max_age: int = constants.DEFAULT_HTTP_CACHE_MAX_AGE,
                         cache_path: Optional[str] = None,
                         offline: bool = False,
                         no_cache: bool = False) -> HttpRequester:
        """
        Initialize the HttpRequester singleton with cache settings.

        :param cache_max_age: Maximum age of cached responses in seconds.
            Negative values mean "never expire".
        :param cache_path: The path to the cache directory.
        :param offline: When ``True``, only cached responses are served.
        :param no_cache: When ``True``, disable the HTTP cache entirely and
            use a plain ``requests.Session``. Incompatible with ``offline``.
        """
        return cls(cache_max_age=cache_max_age, cache_path=cache_path,
                   offline=offline, no_cache=no_cache)

    @classmethod
    def reset(cls) -> None:
        """
        Drop the singleton instance. Primarily intended for tests and the
        ``cache`` CLI subcommand that reconfigures the cache on the fly.
        """
        with cls._lock:
            instance = cls._instance
            if instance is not None:
                try:
                    session = getattr(instance, "session", None)
                    if session is not None and hasattr(session, "close"):
                        session.close()
                except Exception as e:
                    logger.debug("Error closing previous session: %s", e)
                if getattr(instance, "permanent_cache", True) is False:
                    try:
                        instance.cleanup()
                    except Exception as e:
                        logger.debug("Error cleaning up previous cache: %s", e)
            cls._instance = None


class _OfflineFallbackSession:
    """
    Minimal session used when offline mode is requested but no HTTP cache
    backend is available. Every request yields a 504 response to signal a
    cache miss, mirroring the behavior of ``requests_cache`` in offline mode.
    """

    cache = None

    def _offline_response(self, url: str) -> requests.Response:
        response = requests.Response()
        response.status_code = OFFLINE_CACHE_MISS_STATUS
        response.reason = "Offline: no HTTP cache backend available"
        response.url = url
        # response._content = b""
        return response

    def get(self, url, **_kwargs):
        return self._offline_response(url)

    def head(self, url, **_kwargs):
        return self._offline_response(url)

    def post(self, url, **_kwargs):
        return self._offline_response(url)

    def put(self, url, **_kwargs):
        return self._offline_response(url)

    def delete(self, url, **_kwargs):
        return self._offline_response(url)

    def options(self, url, **_kwargs):
        return self._offline_response(url)

    def patch(self, url, **_kwargs):
        return self._offline_response(url)

    def close(self):
        pass
