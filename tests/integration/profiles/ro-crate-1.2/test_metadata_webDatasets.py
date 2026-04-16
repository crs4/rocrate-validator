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

import logging

from rocrate_validator import models
from rocrate_validator.utils.http import HttpRequester
from tests.ro_crates_1_2 import DataEntities
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_data_entities_crates__ = DataEntities()


class _ZipResponse:
    status_code = 200
    headers = {"Content-Type": "application/zip"}
    links = {}

    def raise_for_status(self):
        pass


class _HtmlResponse:
    status_code = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}
    links = {}

    def raise_for_status(self):
        pass


def test_valid_recommended_distribution_downloadable(monkeypatch):
    """
    Dataset whose distribution DataDownload @id returns application/zip passes
    the RECOMMENDED distribution downloadability check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _ZipResponse())

    do_entity_test(
        __metadata_data_entities_crates__.valid_recommended_distribution,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_distribution_not_downloadable(monkeypatch):
    """
    Dataset whose distribution DataDownload @id returns text/html fails the
    RECOMMENDED distribution downloadability check.
    """
    monkeypatch.setattr(HttpRequester(), "head", lambda url, **kw: _HtmlResponse())

    do_entity_test(
        __metadata_data_entities_crates__.invalid_recommended_distribution,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Dataset: distribution downloadability"],
        expected_triggered_issues=["SHOULD be downloadable"],
    )
