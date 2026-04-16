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

from rocrate_validator.utils import log as logging
from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils.signposting import check_downloadable

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Data Entity: citation references")
class DataEntityCitationChecker(PyFunctionCheck):
    """
    Citation references must include an absolute URI.
    """

    @check(name="Data Entity: citation must include @id")
    def check_citation(self, context: ValidationContext) -> bool:
        result = True
        for entity in context.ro_crate.metadata.get_data_entities():
            citations = entity.get_property("citation")
            if citations is None:
                continue
            citation_list = citations if isinstance(citations, list) else [citations]
            for citation in citation_list:
                if isinstance(citation, str):
                    citation_id = citation
                elif hasattr(citation, "id"):
                    citation_id = citation.id
                else:
                    context.result.add_issue(
                        f"Citation for Data Entity '{entity.id}' must reference a publication @id", self)
                    result = False
                    if context.fail_fast:
                        return False
                    continue
                if not re.match(r"^[A-Za-z][A-Za-z0-9+\.-]*:", citation_id):
                    context.result.add_issue(
                        f"Citation for Data Entity '{entity.id}' must be an absolute URI", self)
                    result = False
                    if context.fail_fast:
                        return False
        return result


@requirement(name="Web-based Data Entity: REQUIRED availability")
class WebDataEntityRequiredChecker(PyFunctionCheck):
    """
    Web-based Data Entities SHOULD be directly downloadable (RO-Crate 1.2).
    Downloadability is checked via Signposting, Content-Type, and content negotiation.
    Entities returning an HTML page (splash page / viewer) are also flagged.
    """

    @check(name="Web-based Data Entity: RECOMMENDED resource availability", severity=Severity.RECOMMENDED)
    def check_availability_warning(self, context: ValidationContext) -> bool:
        if context.settings.skip_availability_check:
            return True
        if context.settings.creation_time or context.settings.enforce_availability:
            return True
        if context.settings.metadata_only:
            return True
        result = True
        for entity in context.ro_crate.metadata.get_web_data_entities():
            assert entity.id is not None, "Entity has no @id"
            if entity.id.endswith("/"):
                continue
            try:
                dl = check_downloadable(entity.id)
                if not dl.is_downloadable:
                    if dl.reason and "HTML" in dl.reason:
                        msg = (
                            f"Web-based Data Entity '{entity.id}' references an HTML page "
                            f"(possible splash page or viewer application) and is not "
                            f"directly downloadable"
                        )
                    else:
                        msg = f"Web-based Data Entity '{entity.id}' is not directly downloadable"
                        if dl.reason:
                            msg += f": {dl.reason}"
                    context.result.add_issue(msg, self)
                    result = False
            except Exception as e:
                context.result.add_issue(
                    f"Web-based Data Entity '{entity.id}' availability check failed: {e}", self)
                result = False
            if not result and context.fail_fast:
                return result
        return result

    @check(name="Web-based Data Entity: `contentSize` property", severity=Severity.RECOMMENDED)
    def check_content_size(self, context: ValidationContext) -> bool:
        if context.settings.skip_availability_check:
            return True
        result = True
        for entity in context.ro_crate.metadata.get_web_data_entities():
            assert entity.id is not None, "Entity has no @id"
            if entity.is_available():
                content_size = entity.get_property("contentSize")
                if content_size:
                    if isinstance(content_size, str):
                        content_value = content_size
                    elif hasattr(content_size, "id"):
                        content_value = content_size.id
                    else:
                        content_value = str(content_size)
                    try:
                        content_int = int(str(content_value))
                    except Exception:
                        content_int = None
                    external_size = context.ro_crate.get_external_file_size(entity.id)
                    if external_size is not None and content_int is not None and content_int != external_size:
                        context.result.add_issue(
                            f'The property contentSize={content_size} of the Web-based Data Entity '
                            f'{entity.id} does not match the actual size of '
                            f'the downloadable content, i.e., {external_size} (bytes)', self,
                            violatingEntity=entity.id, violatingProperty='contentSize',
                            violatingPropertyValue=str(content_value))
                        result = False
            if not result and context.fail_fast:
                return result
        return result

    @check(name="Web-based Data Entity: `contentUrl` availability", severity=Severity.RECOMMENDED)
    def check_content_url(self, context: ValidationContext) -> bool:
        if context.settings.skip_availability_check:
            return True
        result = True
        for entity in context.ro_crate.metadata.get_web_data_entities():
            content_url = entity.get_property("contentUrl")
            if not content_url:
                continue
            urls = content_url if isinstance(content_url, list) else [content_url]
            for url in urls:
                url_value = url if isinstance(url, str) else url.id if hasattr(url, "id") else None
                if not url_value or not url_value.startswith("http"):
                    continue
                try:
                    dl = check_downloadable(url_value)
                    if not dl.is_downloadable:
                        msg = f"contentUrl '{url_value}' for Web-based Data Entity '{entity.id}' is not directly downloadable"
                        if dl.reason:
                            msg += f": {dl.reason}"
                        context.result.add_issue(msg, self)
                        result = False
                except Exception as e:
                    context.result.add_issue(
                        f"contentUrl '{url_value}' for Web-based Data Entity '{entity.id}' "
                        f"availability check failed: {e}", self)
                    result = False
                if not result and context.fail_fast:
                    return result
        return result
