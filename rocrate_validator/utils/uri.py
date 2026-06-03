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

import enum
import re
from pathlib import Path
from typing import Optional, Union
from urllib.parse import ParseResult, parse_qsl, urlparse, urlsplit

from rocrate_validator import errors
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester

# set up logging
logger = logging.getLogger(__name__)


class AvailabilityStatus(enum.Enum):
    """Outcome of a URI availability check."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNAUTHORIZED = "unauthorized"
    UNCHECKABLE = "uncheckable"


# RFC 3986 §3.1: scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
# Require length >= 2 to disambiguate from Windows drive letters
# (e.g. ``C:\path``). RFC 3986 allows single-character schemes but no
# IANA-registered scheme is one character long, so this is an acceptable
# trade-off.
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+\-.]+$")


def is_external_reference(value: object) -> bool:
    """
    Check if `value` is an external reference (i.e. has a URI scheme).

    Return True if *value* has an explicit URI or IRI scheme (RFC 3986 for URI, and RFC 3987 for IRIs).
    Both authority-based forms (``http://...``)
    and scheme-only forms (``urn:...``, ``doi:...``, ``arcp://...``) are
    accepted, as required by RO-Crate 1.1 §4.2.2.

    The check is purely syntactic: the scheme is not verified against
    the IANA registry and the hier-part is not resolved.
    """
    if not isinstance(value, str) or not value:
        return False

    try:
        parts = urlsplit(value)
    except ValueError:
        # urlsplit can raise on malformed IPv6 literals, invalid ports, etc.
        return False

    # Scheme must conform to RFC 3986 (and be at least 2 chars long).
    if not _SCHEME_RE.match(parts.scheme):
        return False

    # Reject scheme-only input (``urn:``, ``doi:``): syntactically valid
    # per the grammar but semantically unusable as an identifier.
    return parts.netloc or parts.path or parts.query or parts.fragment


class URI:
    # Schemes that the validator can fetch natively to verify availability.
    # Anything outside this set is treated as remote but un-checkable.
    NATIVELY_CHECKABLE_SCHEMES = ("http", "https")

    # Schemes accepted as RO-Crate root URIs (the loading code can only
    # handle these as crate locations).
    SUPPORTED_ROCRATE_SCHEMES = ("http", "https", "ftp", "file")

    # Well-known remote schemes commonly used to reference data resources
    # (used to distinguish "recognized but un-checkable" from "unknown").
    KNOWN_REMOTE_SCHEMES = (
        # Web
        "http",
        "https",
        # FTP family
        "ftp",
        "ftps",
        "sftp",
        # Remote shell / transfer
        "scp",
        "ssh",
        "rsync",
        # Cloud object stores
        "s3",
        "gs",
        "abfs",
        "abfss",
        "wasb",
        "wasbs",
        # WebDAV
        "dav",
        "davs",
        # Research / big-data filesystems
        "irods",
        "hdfs",
    )

    # ``file://`` authorities that denote the local machine (RFC 8089 §2):
    # an empty authority (``file:///path``) or the special ``localhost`` host.
    LOCAL_FILE_AUTHORITIES = ("", "localhost")

    # Backwards-compatible alias kept for callers that still inspect it.
    REMOTE_SUPPORTED_SCHEMA = SUPPORTED_ROCRATE_SCHEMES[:-1]  # http, https, ftp

    def __init__(self, uri: Union[str, Path]):
        if uri is None or (isinstance(uri, str) and not uri.strip()):
            raise ValueError("Invalid URI: empty value")
        self._uri = uri = str(uri)
        try:
            # Inputs that are not external references are assumed to be local
            # paths, so the ``file:`` scheme is added explicitly. The
            # detection covers both authority-based schemes (``http://``,
            # ``scp://``) and scheme-only ones (``urn:``, ``doi:``), as
            # defined by RFC 3986.
            #
            # The authority-less ``file:`` form (no ``//``) is used on purpose:
            # ``file://data/x`` would parse ``data`` as the authority (host),
            # while ``file:data/x`` keeps ``data/x`` as the path with an empty
            # authority. This way a local path never gains a spurious host and
            # the authority remains a reliable signal to tell a local file
            # (``file:///path``) from a remote one (``file://host/path``,
            # RFC 8089).
            if not is_external_reference(uri):
                uri = f"file:{uri}"
            # parse the value to extract the scheme
            self._parse_result = urlparse(uri)
            if not self.scheme:
                raise ValueError("URI has no scheme")
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(e)
            raise ValueError(f"Invalid URI: {uri}") from e

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
        """
        Return True for any well-formed URI that points to a non-local resource.

        Schemes other than ``file`` (``http``, ``scp``, ``s3``, ...) are always
        remote. A ``file://`` URI is remote when it carries an explicit,
        non-local authority (host) — e.g. ``file://hostname/path`` per
        RFC 8089: the referenced file lives on another machine and is therefore
        not part of the local RO-Crate payload.
        """
        if not self.scheme:
            return False
        if self.scheme == "file":
            return self.get_netloc().lower() not in self.LOCAL_FILE_AUTHORITIES
        return True

    def is_local_resource(self) -> bool:
        return self.scheme == "file" and self.get_netloc().lower() in self.LOCAL_FILE_AUTHORITIES

    def is_natively_checkable(self) -> bool:
        """Return True if availability can be verified via a native request."""
        return self.scheme in self.NATIVELY_CHECKABLE_SCHEMES

    def is_known_remote_scheme(self) -> bool:
        """Return True if the scheme is one of the well-known remote schemes."""
        return self.scheme in self.KNOWN_REMOTE_SCHEMES

    def has_supported_rocrate_scheme(self) -> bool:
        """Return True if the scheme is supported as an RO-Crate root URI."""
        return self.scheme in self.SUPPORTED_ROCRATE_SCHEMES

    def is_local_directory(self) -> bool:
        return self.is_local_resource() and self.as_path().is_dir()

    def is_local_file(self) -> bool:
        return self.is_local_resource() and self.as_path().is_file()

    def check_availability(self) -> AvailabilityStatus:
        """
        Inspect the resource availability with as much detail as possible.

        Distinguishes:
          - AVAILABLE: confirmed reachable
          - UNAUTHORIZED: reachable but protected (HTTP 401/403)
          - UNAVAILABLE: confirmed not reachable
          - UNCHECKABLE: scheme has no native check (e.g. scp://, s3://)
        """
        if self.is_remote_resource():
            if not self.is_natively_checkable():
                logger.debug(
                    "Cannot natively verify availability for URI '%s' (scheme '%s')",
                    self._uri,
                    self.scheme,
                )
                return AvailabilityStatus.UNCHECKABLE
            try:
                response = HttpRequester().head(self._uri, allow_redirects=True)
                if response.status_code in (200, 302):
                    return AvailabilityStatus.AVAILABLE
                if response.status_code in (401, 403):
                    return AvailabilityStatus.UNAUTHORIZED
                return AvailabilityStatus.UNAVAILABLE
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(e)
                return AvailabilityStatus.UNAVAILABLE
        return AvailabilityStatus.AVAILABLE if Path(self._uri).exists() else AvailabilityStatus.UNAVAILABLE

    def is_available(self) -> bool:
        """
        Return True only when the resource is confirmed available.

        Resources that cannot be verified (unsupported scheme, auth-protected)
        return False here; callers that need to distinguish those cases should
        use :meth:`check_availability` instead.
        """
        return self.check_availability() == AvailabilityStatus.AVAILABLE

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
            uri = URI(str(uri)) if isinstance(uri, (str, Path)) else uri
            # restrict RO-Crate roots to schemes the loader can actually handle
            if not uri.has_supported_rocrate_scheme():
                raise errors.ROCrateInvalidURIError(uri)
            # check if the URI is a remote resource or local directory or local file
            if not uri.is_remote_resource() and not uri.is_local_directory() and not uri.is_local_file():
                raise errors.ROCrateInvalidURIError(uri)
            # check if the local file is a ZIP file
            if uri.is_local_file() and uri.as_path().suffix != ".zip":
                raise errors.ROCrateInvalidURIError(uri)
            # check if the resource is available
            if not uri.is_available():
                raise errors.ROCrateInvalidURIError(uri, message=f'The RO-crate at the URI "{uri}" is not available')
            return True
        except ValueError as e:
            logger.error(e)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            raise errors.ROCrateInvalidURIError(uri) from e
    except Exception as e:
        if not silent:
            raise e
        return False
