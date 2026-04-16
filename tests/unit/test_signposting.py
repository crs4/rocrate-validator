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

"""Unit tests for rocrate_validator.utils.signposting.check_downloadable."""


from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.signposting import (_HTML_MIME_TYPES,
                                                 _ROCRATE_ACCEPT,
                                                 DownloadabilityResult,
                                                 DownloadVia,
                                                 check_downloadable)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_URL = "https://example.com/rocrate"


class _HeadResponse:
    """Minimal fake HEAD response sufficient for check_downloadable."""

    def __init__(
        self,
        status_code: int = 200,
        content_type: str | None = None,
        links: dict | None = None,
        raise_on_status: bool = False,
    ):
        self.status_code = status_code
        self.headers: dict = {}
        if content_type is not None:
            self.headers["Content-Type"] = content_type
        self.links: dict = links or {}
        self._raise = raise_on_status

    def raise_for_status(self):
        if self._raise:
            raise RuntimeError(f"HTTP {self.status_code}")


def _html_resp(**kw) -> _HeadResponse:
    return _HeadResponse(content_type="text/html", **kw)


def _zip_resp(**kw) -> _HeadResponse:
    return _HeadResponse(content_type="application/zip", **kw)


# ---------------------------------------------------------------------------
# Data-model tests
# ---------------------------------------------------------------------------
class TestDownloadVia:

    def test_enum_string_values(self):
        assert DownloadVia.DIRECT == "direct"
        assert DownloadVia.SIGNPOSTING_ITEM == "signposting_item"
        assert DownloadVia.SIGNPOSTING_DESCRIBEDBY == "signposting_describedby"
        assert DownloadVia.CONTENT_NEGOTIATION == "content_negotiation"

    def test_all_values_are_strings(self):
        for member in DownloadVia:
            assert isinstance(member.value, str)


class TestDownloadabilityResult:

    def test_downloadable_result_fields(self):
        r = DownloadabilityResult(
            is_downloadable=True,
            via=DownloadVia.DIRECT,
            download_url=_URL,
        )
        assert r.is_downloadable is True
        assert r.via == DownloadVia.DIRECT
        assert r.download_url == _URL
        assert r.reason is None

    def test_not_downloadable_result_fields(self):
        r = DownloadabilityResult(is_downloadable=False, reason="no luck")
        assert r.is_downloadable is False
        assert r.via is None
        assert r.download_url is None
        assert r.reason == "no luck"

    def test_defaults_are_none(self):
        r = DownloadabilityResult(is_downloadable=True)
        assert r.via is None
        assert r.download_url is None
        assert r.reason is None


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
class TestModuleConstants:

    def test_html_mime_types_contains_text_html(self):
        assert "text/html" in _HTML_MIME_TYPES

    def test_html_mime_types_contains_xhtml(self):
        assert "application/xhtml+xml" in _HTML_MIME_TYPES

    def test_html_mime_types_does_not_contain_json(self):
        assert "application/json" not in _HTML_MIME_TYPES
        assert "application/ld+json" not in _HTML_MIME_TYPES
        assert "application/zip" not in _HTML_MIME_TYPES

    def test_rocrate_accept_includes_json_ld(self):
        assert "application/ld+json" in _ROCRATE_ACCEPT

    def test_rocrate_accept_includes_zip(self):
        assert "application/zip" in _ROCRATE_ACCEPT


# ---------------------------------------------------------------------------
# Signposting (RFC 8288 Link headers)
# ---------------------------------------------------------------------------
class TestSignpostingItemLink:

    def test_item_link_is_downloadable(self, monkeypatch):
        item_url = "https://example.com/rocrate.zip"
        resp = _HeadResponse(links={"item": {"url": item_url}})
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.is_downloadable is True

    def test_item_link_via(self, monkeypatch):
        resp = _HeadResponse(links={"item": {"url": "https://example.com/rocrate.zip"}})
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.via == DownloadVia.SIGNPOSTING_ITEM

    def test_item_link_download_url(self, monkeypatch):
        item_url = "https://example.com/rocrate.zip"
        resp = _HeadResponse(links={"item": {"url": item_url}})
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.download_url == item_url

    def test_item_link_empty_dict_is_falsy_not_downloadable(self, monkeypatch):
        """rel=item whose value is an empty dict is falsy → treated as absent, falls through."""
        # In Python `if {}` is False, so `if item_link:` skips an empty-dict entry.
        resp = _HeadResponse(links={"item": {}})
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        # The empty dict is falsy; the code does not enter the Signposting branch.
        assert result.via != DownloadVia.SIGNPOSTING_ITEM


class TestSignpostingDescribedByLink:

    def test_describedby_link_is_downloadable(self, monkeypatch):
        meta_url = "https://example.com/ro-crate-metadata.json"
        resp = _HeadResponse(links={"describedby": {"url": meta_url}})
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.is_downloadable is True

    def test_describedby_link_via(self, monkeypatch):
        resp = _HeadResponse(links={"describedby": {"url": "https://example.com/meta.json"}})
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.via == DownloadVia.SIGNPOSTING_DESCRIBEDBY

    def test_describedby_link_download_url(self, monkeypatch):
        meta_url = "https://example.com/ro-crate-metadata.json"
        resp = _HeadResponse(links={"describedby": {"url": meta_url}})
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.download_url == meta_url


class TestSignpostingPriority:

    def test_item_takes_priority_over_describedby(self, monkeypatch):
        """When both rel=item and rel=describedby are present, rel=item wins."""
        resp = _HeadResponse(links={
            "item": {"url": "https://example.com/rocrate.zip"},
            "describedby": {"url": "https://example.com/meta.json"},
        })
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.via == DownloadVia.SIGNPOSTING_ITEM
        assert result.download_url == "https://example.com/rocrate.zip"

    def test_signposting_takes_priority_over_direct_content_type(self, monkeypatch):
        """A Signposting link wins over a non-HTML Content-Type on the same response."""
        resp = _HeadResponse(
            content_type="application/zip",
            links={"item": {"url": "https://example.com/rocrate.zip"}},
        )
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.via == DownloadVia.SIGNPOSTING_ITEM


# ---------------------------------------------------------------------------
# Direct download (Content-Type based)
# ---------------------------------------------------------------------------
class TestDirectDownload:

    def test_zip_content_type(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _zip_resp())

        result = check_downloadable(_URL)

        assert result.is_downloadable is True
        assert result.via == DownloadVia.DIRECT

    def test_direct_download_url_equals_checked_url(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _zip_resp())

        result = check_downloadable(_URL)

        assert result.download_url == _URL

    def test_json_ld_content_type(self, monkeypatch):
        resp = _HeadResponse(content_type="application/ld+json")
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.is_downloadable is True
        assert result.via == DownloadVia.DIRECT

    def test_content_type_with_charset_suffix(self, monkeypatch):
        """charset suffix is stripped before the MIME type comparison."""
        resp = _HeadResponse(content_type="application/json; charset=utf-8")
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.is_downloadable is True
        assert result.via == DownloadVia.DIRECT

    def test_text_html_is_not_direct(self, monkeypatch):
        """text/html must not be treated as a direct download."""
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _html_resp())

        result = check_downloadable(_URL)

        assert result.via != DownloadVia.DIRECT

    def test_xhtml_is_not_direct(self, monkeypatch):
        """application/xhtml+xml is in _HTML_MIME_TYPES and must not be direct."""
        resp = _HeadResponse(content_type="application/xhtml+xml")
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.via != DownloadVia.DIRECT

    def test_missing_content_type_header_is_not_direct(self, monkeypatch):
        """No Content-Type header → empty string → falsy → falls through, not DIRECT."""
        resp = _HeadResponse()  # no content_type kwarg → headers dict is empty
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.via != DownloadVia.DIRECT


# ---------------------------------------------------------------------------
# Content negotiation
# ---------------------------------------------------------------------------
class TestContentNegotiation:

    def _make_neg_head(self, plain_ct: str, neg_ct: str, neg_status: int = 200):
        """Return a fake_head function that differentiates plain and Accept-based calls."""
        def fake_head(url, **kwargs):
            if kwargs.get("headers", {}).get("Accept"):
                return _HeadResponse(status_code=neg_status, content_type=neg_ct)
            return _HeadResponse(content_type=plain_ct)
        return fake_head

    def test_content_negotiation_success(self, monkeypatch):
        monkeypatch.setattr(
            HttpRequester(), "head",
            self._make_neg_head("text/html", "application/ld+json"),
        )

        result = check_downloadable(_URL)

        assert result.is_downloadable is True
        assert result.via == DownloadVia.CONTENT_NEGOTIATION

    def test_content_negotiation_download_url_equals_checked_url(self, monkeypatch):
        monkeypatch.setattr(
            HttpRequester(), "head",
            self._make_neg_head("text/html", "application/ld+json"),
        )

        result = check_downloadable(_URL)

        assert result.download_url == _URL

    def test_content_negotiation_zip_response(self, monkeypatch):
        monkeypatch.setattr(
            HttpRequester(), "head",
            self._make_neg_head("text/html", "application/zip"),
        )

        result = check_downloadable(_URL)

        assert result.is_downloadable is True
        assert result.via == DownloadVia.CONTENT_NEGOTIATION

    def test_content_negotiation_html_response_not_downloadable(self, monkeypatch):
        """Accept-based HEAD also returns HTML → not downloadable."""
        monkeypatch.setattr(
            HttpRequester(), "head",
            self._make_neg_head("text/html", "text/html"),
        )

        result = check_downloadable(_URL)

        assert result.is_downloadable is False

    def test_content_negotiation_non_200_status_not_downloadable(self, monkeypatch):
        """Accept-based HEAD returns 404 → content negotiation does not count."""
        monkeypatch.setattr(
            HttpRequester(), "head",
            self._make_neg_head("text/html", "application/ld+json", neg_status=404),
        )

        result = check_downloadable(_URL)

        assert result.is_downloadable is False

    def test_content_negotiation_accept_header_value(self, monkeypatch):
        """The second HEAD request MUST carry the RO-Crate Accept header."""
        captured: dict = {}

        def fake_head(url, **kwargs):
            hdrs = kwargs.get("headers", {})
            if hdrs.get("Accept"):
                captured["accept"] = hdrs["Accept"]
                return _HeadResponse(status_code=200, content_type="application/ld+json")
            return _HeadResponse(content_type="text/html")

        monkeypatch.setattr(HttpRequester(), "head", fake_head)
        check_downloadable(_URL)

        assert "accept" in captured, "Second HEAD must send an Accept header"
        assert "application/ld+json" in captured["accept"]
        assert "application/zip" in captured["accept"]

    def test_only_one_head_call_when_direct(self, monkeypatch):
        """Direct download path must NOT trigger a second HEAD for content negotiation."""
        call_count = [0]

        def fake_head(url, **kwargs):
            call_count[0] += 1
            return _zip_resp()

        monkeypatch.setattr(HttpRequester(), "head", fake_head)
        check_downloadable(_URL)

        assert call_count[0] == 1

    def test_only_one_head_call_when_signposting(self, monkeypatch):
        """Signposting path must NOT trigger a second HEAD."""
        call_count = [0]

        def fake_head(url, **kwargs):
            call_count[0] += 1
            return _HeadResponse(links={"item": {"url": "https://example.com/rocrate.zip"}})

        monkeypatch.setattr(HttpRequester(), "head", fake_head)
        check_downloadable(_URL)

        assert call_count[0] == 1


# ---------------------------------------------------------------------------
# Not downloadable result
# ---------------------------------------------------------------------------
class TestNotDownloadable:

    def test_not_downloadable_is_false(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _html_resp())

        result = check_downloadable(_URL)

        assert result.is_downloadable is False

    def test_not_downloadable_via_is_none(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _html_resp())

        result = check_downloadable(_URL)

        assert result.via is None

    def test_not_downloadable_download_url_is_none(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _html_resp())

        result = check_downloadable(_URL)

        assert result.download_url is None

    def test_not_downloadable_reason_mentions_signposting(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _html_resp())

        result = check_downloadable(_URL)

        assert result.reason is not None
        assert "Signposting" in result.reason

    def test_not_downloadable_reason_mentions_html(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _html_resp())

        result = check_downloadable(_URL)

        assert "HTML" in result.reason

    def test_not_downloadable_reason_mentions_content_negotiation(self, monkeypatch):
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _html_resp())

        result = check_downloadable(_URL)

        assert "content negotiation" in result.reason


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:

    def test_http_error_status_not_downloadable(self, monkeypatch):
        """raise_for_status() raises → is_downloadable is False."""
        resp = _HeadResponse(status_code=404, raise_on_status=True)
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.is_downloadable is False

    def test_http_error_reason_contains_message(self, monkeypatch):
        """The exception message is propagated to DownloadabilityResult.reason."""
        resp = _HeadResponse(status_code=404, raise_on_status=True)
        monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: resp)

        result = check_downloadable(_URL)

        assert result.reason is not None
        assert "HTTP 404" in result.reason

    def test_connection_error_not_downloadable(self, monkeypatch):
        def fake_head(url, **kwargs):
            raise ConnectionError("Connection refused")

        monkeypatch.setattr(HttpRequester(), "head", fake_head)

        result = check_downloadable(_URL)

        assert result.is_downloadable is False

    def test_connection_error_reason(self, monkeypatch):
        def fake_head(url, **kwargs):
            raise ConnectionError("Connection refused")

        monkeypatch.setattr(HttpRequester(), "head", fake_head)

        result = check_downloadable(_URL)

        assert "Connection refused" in result.reason

    def test_timeout_error_not_downloadable(self, monkeypatch):
        def fake_head(url, **kwargs):
            raise TimeoutError("Timed out")

        monkeypatch.setattr(HttpRequester(), "head", fake_head)

        result = check_downloadable(_URL)

        assert result.is_downloadable is False

    def test_generic_exception_not_downloadable(self, monkeypatch):
        def fake_head(url, **kwargs):
            raise ValueError("unexpected error")

        monkeypatch.setattr(HttpRequester(), "head", fake_head)

        result = check_downloadable(_URL)

        assert result.is_downloadable is False
        assert "unexpected error" in result.reason

    def test_error_handling_never_raises(self, monkeypatch):
        """check_downloadable must never propagate exceptions to the caller."""
        def fake_head(url, **kwargs):
            raise RuntimeError("catastrophic failure")

        monkeypatch.setattr(HttpRequester(), "head", fake_head)

        # Must not raise
        result = check_downloadable(_URL)
        assert isinstance(result, DownloadabilityResult)
