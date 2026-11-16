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

import io
import re
import zipfile
from pathlib import Path

import pytest
from requests import HTTPError, Response

from rocrate_validator.rocrate import BagitROCrate, ROCrate, ROCrateBagitRemoteZip, ROCrateRemoteZip
from rocrate_validator.utils.http import HttpRequester

URL = "https://example.org/bagit.zip"
METADATA = b'{"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": []}'


@pytest.fixture(name="remote_zip")
def remote_zip_fixture(monkeypatch):
    """Model servers rejecting suffix ranges, without making any network requests."""

    def install(
        *,
        comment=b"",
        ignore_range=False,
        status=206,
        truncate=False,
        bad_content_range=False,
        compression=zipfile.ZIP_STORED,
        bagit=True,
    ):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
            if bagit:
                archive.writestr("bagit.txt", "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n")
            archive.writestr("data/ro-crate-metadata.json", METADATA)
            archive.writestr("data/large.bin", b"x" * 200_000)
            archive.comment = comment
        payload = buffer.getvalue()
        ranges = []

        def response(code, content=b"", **headers):
            result = Response()
            result.status_code = code
            result.url = URL
            result._content = content  # pylint: disable=protected-access
            result.headers.update(headers)
            return result

        def head(_self, url, **_kwargs):
            assert url == URL
            if not _kwargs.get("allow_redirects"):
                return response(302, **{"Content-Length": "0", "Location": URL + "?redirected"})
            return response(200, **{"Content-Length": str(len(payload))})

        def get(_self, url, *, headers, **_kwargs):
            assert url == URL
            match = re.fullmatch(r"bytes=(\d+)-(\d+)", headers.get("Range", ""))
            if not match:
                return response(501)
            start, end = map(int, match.groups())
            assert 0 <= start <= end < len(payload)
            ranges.append((start, end))
            if ignore_range:
                return response(200, payload[:-1] if truncate else payload)
            content = payload[start : end + 1]
            return response(
                status,
                content[:-1] if truncate else content,
                **{"Content-Range": "bytes 0-0/1" if bad_content_range else f"bytes {start}-{end}/{len(payload)}"},
            )

        monkeypatch.setattr(HttpRequester, "head", head, raising=False)
        monkeypatch.setattr(HttpRequester, "get", get, raising=False)
        return payload, ranges

    return install


@pytest.mark.parametrize("ignore_range", [False, True])
@pytest.mark.parametrize("comment", [b"", b"Archive comment" * 100])
def test_remote_zip_reads_entries_with_absolute_ranges(remote_zip, ignore_range, comment, caplog):
    payload, ranges = remote_zip(comment=comment, ignore_range=ignore_range)
    with caplog.at_level("WARNING", logger="rocrate_validator.utils.http"):
        crate = ROCrateRemoteZip(URL)

        assert crate.has_file(Path("bagit.txt"))
        assert crate.get_file_content(Path("data/ro-crate-metadata.json")) == METADATA
        assert crate.get_file_content(Path("data/ro-crate-metadata.json"), binary_mode=False) == METADATA.decode()
        assert crate.get_file_size(Path("data/large.bin")) == 200_000
    assert ranges
    # Inspecting the directory and reading metadata must not download the large payload.
    assert sum(end - start + 1 for start, end in ranges) < len(payload)
    if ignore_range:
        assert len(ranges) == 1, "Reuse the full response when the server ignores Range"
        assert len(caplog.records) == 1
        assert "Server ignored HTTP Range" in caplog.text
        assert URL in caplog.text
        assert f"{len(payload)} bytes" in caplog.text
        assert "retained in memory" in caplog.text
    else:
        assert not caplog.records


@pytest.mark.parametrize("ignore_range", [False, True])
@pytest.mark.parametrize("bagit", [False, True])
def test_remote_zip_bagit_detection_and_factory(remote_zip, ignore_range, bagit):
    remote_zip(ignore_range=ignore_range, bagit=bagit)

    assert BagitROCrate.is_bagit_wrapping_crate(URL) is bagit
    crate = ROCrate.new_instance(URL)
    assert isinstance(crate, ROCrateRemoteZip)
    assert isinstance(crate, ROCrateBagitRemoteZip) is bagit
    path = "ro-crate-metadata.json" if bagit else "data/ro-crate-metadata.json"
    assert crate.get_file_content(Path(path)) == METADATA


@pytest.mark.parametrize("status", [403, 404, 503])
def test_remote_zip_propagates_range_http_errors(remote_zip, status):
    remote_zip(status=status)

    with pytest.raises(HTTPError, match=str(status)):
        ROCrateRemoteZip(URL)


@pytest.mark.parametrize("ignore_range", [False, True])
def test_remote_zip_rejects_truncated_range_response(remote_zip, ignore_range):
    remote_zip(truncate=True, ignore_range=ignore_range)

    with pytest.raises(OSError, match="range response"):
        ROCrateRemoteZip(URL)


def test_remote_zip_rejects_wrong_content_range(remote_zip):
    remote_zip(bad_content_range=True)

    with pytest.raises(OSError, match="range response"):
        ROCrateRemoteZip(URL)


def test_remote_zip_reads_compressed_entries(remote_zip):
    remote_zip(compression=zipfile.ZIP_DEFLATED)
    crate = ROCrateRemoteZip(URL)

    assert crate.get_file_content(Path("data/ro-crate-metadata.json")) == METADATA
    assert crate.get_file_content(Path("data/large.bin")) == b"x" * 200_000
    with pytest.raises(FileNotFoundError):
        crate.get_file_content(Path("missing.txt"))
