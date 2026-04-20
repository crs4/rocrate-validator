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
from typing import Optional

import requests

from rocrate_validator import constants
from rocrate_validator.utils import log as logging

# set up logging
logger = logging.getLogger(__name__)


class HttpRequester:
    """
    A singleton class to handle HTTP requests
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
                 cache_path: Optional[str] = None):
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
            if cache_max_age >= 0:
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
                # Initialize the session with a cache
                self.session = CachedSession(
                    # Cache name with random suffix
                    cache_name=cache_path,
                    expire_after=cache_max_age,  # Cache expiration time in seconds
                    backend='sqlite',  # Use SQLite backend
                    allowable_methods=('GET',),  # Cache GET
                    allowable_codes=(200, 302, 404)  # Cache responses with these status codes
                )
        except ImportError:
            logger.warning("requests_cache is not installed. Using requests instead.")
        except Exception as e:
            logger.error("Error initializing requests_cache: %s", e)

        # if requests_cache is not installed or an error occurred,
        # use requests instead of requests_cache
        # and create a new session
        if not self.session:
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
        Destructor to clean up the cache file used by CachedSession.
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
        Delegate HTTP methods to the session object.

        :param name: The name of the method to call.
        :return: The method from the session object.
        """
        if name.upper() in {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"}:
            return getattr(self.session, name.lower())
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    @classmethod
    def initialize_cache(cls,
                         cache_max_age: int = constants.DEFAULT_HTTP_CACHE_MAX_AGE,
                         cache_path: Optional[str] = None) -> HttpRequester:
        """
        Initialize the HttpRequester singleton with cache settings.

        :param max_age: The maximum age of the cache in seconds.
        :param cache_path: The path to the cache directory.
        """
        return cls(cache_max_age=cache_max_age, cache_path=cache_path)
