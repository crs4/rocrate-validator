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

import re
from pathlib import Path
from typing import Optional, Union
from urllib.parse import ParseResult, parse_qsl, urlparse

from rocrate_validator import errors
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester

# set up logging
logger = logging.getLogger(__name__)


class URI:

    REMOTE_SUPPORTED_SCHEMA = ('http', 'https', 'ftp')

    def __init__(self, uri: Union[str, Path]):
        self._uri = uri = str(uri)
        try:
            # map local path to URI with file scheme
            if not re.match(r'^\w+://', uri):
                uri = f"file://{uri}"
            # parse the value to extract the scheme
            self._parse_result = urlparse(uri)
            assert self.scheme in self.REMOTE_SUPPORTED_SCHEMA + ('file',), "Invalid URI scheme"
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(e)
            raise ValueError("Invalid URI: %s" % uri)

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def base_uri(self) -> str:
        return f"{self.scheme}://{self._parse_result.netloc}{self._parse_result.path}"

    @property
    def parse_result(self) -> ParseResult:
        return self._parse_result

    @property
    def scheme(self) -> str:
        return self._parse_result.scheme

    @property
    def fragment(self) -> Optional[str]:
        fragment = self._parse_result.fragment
        return fragment if fragment else None

    def get_scheme(self) -> str:
        return self._parse_result.scheme

    def get_netloc(self) -> str:
        return self._parse_result.netloc

    def get_path(self) -> str:
        return self._parse_result.path

    def get_query_string(self) -> str:
        return self._parse_result.query

    def get_query_param(self, param: str) -> Optional[str]:
        query_params = dict(parse_qsl(self._parse_result.query))
        return query_params.get(param)

    def as_path(self) -> Path:
        if not self.is_local_resource():
            raise ValueError("URI is not a local resource")
        return Path(self._uri)

    def is_remote_resource(self) -> bool:
        return self.scheme in self.REMOTE_SUPPORTED_SCHEMA

    def is_local_resource(self) -> bool:
        return not self.is_remote_resource()

    def is_local_directory(self) -> bool:
        return self.is_local_resource() and self.as_path().is_dir()

    def is_local_file(self) -> bool:
        return self.is_local_resource() and self.as_path().is_file()

    def is_available(self) -> bool:
        """Check if the resource is available"""
        if self.is_remote_resource():
            try:
                response = HttpRequester().head(self._uri, allow_redirects=True)
                return response.status_code in (200, 302)
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(e)
                return False
        return Path(self._uri).exists()

    def __str__(self):
        return self._uri

    def __repr__(self):
        return f"URI(uri={self._uri})"

    def __eq__(self, other):
        if isinstance(other, URI):
            return self._uri == other.uri
        return False

    def __hash__(self):
        return hash(self._uri)


def validate_rocrate_uri(uri: Union[str, Path, URI], silent: bool = False) -> bool:
    """
    Validate the RO-Crate URI

    :param uri: The RO-Crate URI to validate. Can be a string, Path, or URI object
    :param silent: If True, do not raise an exception
    :return: True if the URI is valid, False otherwise
    """
    try:
        assert uri, "The RO-Crate URI is required"
        assert isinstance(uri, (str, Path, URI)), "The RO-Crate URI must be a string, Path, or URI object"
        try:
            # parse the value to extract the scheme
            uri = URI(str(uri)) if isinstance(uri, str) or isinstance(uri, Path) else uri
            # check if the URI is a remote resource or local directory or local file
            if not uri.is_remote_resource() and not uri.is_local_directory() and not uri.is_local_file():
                raise errors.ROCrateInvalidURIError(uri)
            # check if the local file is a ZIP file
            if uri.is_local_file() and uri.as_path().suffix != ".zip":
                raise errors.ROCrateInvalidURIError(uri)
            # check if the resource is available
            if not uri.is_available():
                raise errors.ROCrateInvalidURIError(uri, message=f"The RO-crate at the URI \"{uri}\" is not available")
            return True
        except ValueError as e:
            logger.error(e)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            raise errors.ROCrateInvalidURIError(uri)
    except Exception as e:
        if not silent:
            raise e
        return False
