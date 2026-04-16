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
Utilities for checking resource downloadability via Signposting (RFC 8574),
direct content-type inspection, and HTTP content negotiation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester

logger = logging.getLogger(__name__)


# MIME types that indicate a landing/navigation page, not directly downloadable content
_HTML_MIME_TYPES = frozenset({"text/html", "application/xhtml+xml"})

# Accept header used when attempting content negotiation for RO-Crate metadata/archives.
# The profile parameter is included per RO-Crate 1.2 spec to disambiguate RO-Crate content
# from generic JSON-LD or ZIP resources (see signposting.md for details).
_ROCRATE_ACCEPT = (
    'application/ld+json; profile="https://w3id.org/ro/crate", '
    "application/ld+json;q=0.9, "
    "application/json;q=0.8, "
    "application/zip;q=0.7"
)


class DownloadVia(str, Enum):
    """Mechanism through which a URL was determined to be downloadable."""
    DIRECT = "direct"
    SIGNPOSTING_ITEM = "signposting_item"
    SIGNPOSTING_DESCRIBEDBY = "signposting_describedby"
    CONTENT_NEGOTIATION = "content_negotiation"


@dataclass
class DownloadabilityResult:
    """
    Result of a downloadability check.

    :param is_downloadable: True if the URL ultimately provides a downloadable item.
    :param via: The mechanism through which downloadability was determined.
    :param download_url: The concrete URL of the downloadable resource (may differ
                         from the checked URL when resolved via Signposting).
    :param reason: Human-readable explanation when ``is_downloadable`` is False.
    """
    is_downloadable: bool
    via: Optional[DownloadVia] = None
    download_url: Optional[str] = None
    reason: Optional[str] = None


def check_downloadable(url: str) -> DownloadabilityResult:
    """
    Check whether *url* ultimately provides a downloadable item, following the
    RO-Crate 1.2 / RFC 8574 requirements for ``cite-as`` targets.

    The function probes the URL in the following order:

    1. **Signposting** — parses the ``Link`` response headers (RFC 8288).
       A ``rel="item"`` link indicates a downloadable archive; a
       ``rel="describedby"`` link indicates a retrievable metadata document.
    2. **Direct download** — if the ``Content-Type`` of the HEAD response is
       not an HTML MIME type the resource is considered directly downloadable.
    3. **Content negotiation** — a second HEAD request is issued with
       ``Accept: application/ld+json, …``.  If the server returns a non-HTML
       ``Content-Type`` the resource is reachable via content negotiation.

    :param url: The URL to check.
    :returns: A :class:`DownloadabilityResult` instance.
    :raises: Does **not** raise; all HTTP errors are captured in
             ``DownloadabilityResult.reason``.
    """
    try:
        response = HttpRequester().head(url, allow_redirects=True)
        response.raise_for_status()

        # -- 1. Signposting (RFC 8288 Link headers) ---------------------------
        # requests parses all Link headers into response.links keyed by rel.
        links = response.links

        item_link = links.get("item")
        if item_link:
            logger.error("cite-as '%s' is downloadable via Signposting rel=item: %s",
                         url, item_link.get("url"))
            return DownloadabilityResult(
                is_downloadable=True,
                via=DownloadVia.SIGNPOSTING_ITEM,
                download_url=item_link.get("url"),
            )

        describedby_link = links.get("describedby")
        if describedby_link:
            logger.error("cite-as '%s' is downloadable via Signposting rel=describedby: %s",
                         url, describedby_link.get("url"))
            return DownloadabilityResult(
                is_downloadable=True,
                via=DownloadVia.SIGNPOSTING_DESCRIBEDBY,
                download_url=describedby_link.get("url"),
            )

        # -- 2. Direct download -----------------------------------------------
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        if content_type and content_type not in _HTML_MIME_TYPES:
            logger.error("cite-as '%s' is directly downloadable (Content-Type: %s)",
                         url, content_type)
            return DownloadabilityResult(
                is_downloadable=True,
                via=DownloadVia.DIRECT,
                download_url=url,
            )

        # -- 3. Content negotiation -------------------------------------------
        neg_response = HttpRequester().head(
            url,
            headers={"Accept": _ROCRATE_ACCEPT},
            allow_redirects=True,
        )
        if neg_response.status_code == 200:
            neg_ct = neg_response.headers.get("Content-Type", "").split(";")[0].strip()
            if neg_ct and neg_ct not in _HTML_MIME_TYPES:
                logger.error(
                    "cite-as '%s' is downloadable via content negotiation (Content-Type: %s)",
                    url, neg_ct,
                )
                return DownloadabilityResult(
                    is_downloadable=True,
                    via=DownloadVia.CONTENT_NEGOTIATION,
                    download_url=url,
                )

        # -- Not downloadable -------------------------------------------------
        return DownloadabilityResult(
            is_downloadable=False,
            reason=(
                "No Signposting links (rel='item' or rel='describedby') found, "
                "Content-Type is HTML, and content negotiation did not yield a "
                "downloadable format"
            ),
        )

    except Exception as e:
        logger.error("Error checking downloadability of '%s': %s", url, e, exc_info=True)
        return DownloadabilityResult(
            is_downloadable=False,
            reason=str(e),
        )
