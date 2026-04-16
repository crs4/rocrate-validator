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

from rocrate_validator.utils import log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils.signposting import check_downloadable

logger = logging.getLogger(__name__)


@requirement(name="Root Data Entity: `cite-as` downloadability")
class CiteAsDownloadableChecker(PyFunctionCheck):
    """
    If present, the `cite-as` value of the Root Data Entity MUST ultimately
    provide the RO-Crate as a downloadable item, accessible via Signposting
    (Link rel="item" or rel="describedby"), direct download, or content
    negotiation (RO-Crate 1.2, RFC 8574).
    """

    @check(name="Root Data Entity: `cite-as` MUST reference a downloadable item")
    def check_cite_as_downloadable(self, context: ValidationContext) -> bool:
        if context.settings.skip_availability_check:
            return True
        if not (context.settings.creation_time or context.settings.enforce_availability):
            return True
        if context.settings.metadata_only:
            return True

        try:
            root_entity = context.ro_crate.metadata.get_root_data_entity()
            cite_as_raw = root_entity.get_property("cite-as")
            if not cite_as_raw:
                return True

            # cite-as can be a plain string literal or an entity reference {"@id": "..."}
            if isinstance(cite_as_raw, str):
                cite_as_url = cite_as_raw
            elif hasattr(cite_as_raw, "id"):
                cite_as_url = cite_as_raw.id
            else:
                return True

            if not cite_as_url or not cite_as_url.startswith("http"):
                return True

            result = check_downloadable(cite_as_url)
            if not result.is_downloadable:
                context.result.add_issue(
                    f"The `cite-as` value '{cite_as_url}' MUST ultimately provide "
                    f"the RO-Crate as a downloadable item"
                    + (f": {result.reason}" if result.reason else ""),
                    self,
                )
                return False

            logger.debug(
                "cite-as '%s' is downloadable via %s (url: %s)",
                cite_as_url, result.via, result.download_url,
            )
            return True

        except Exception as e:
            context.result.add_issue(
                f"Error checking `cite-as` downloadability: {str(e)}", self)
            return False
