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

from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.signposting import check_downloadable

logger = logging.getLogger(__name__)


def _resolve_distribution_url(dist) -> str | None:
    """
    Extract the download URL from a distribution value.

    The distribution property can be:
    - A plain string URL
    - A DataDownload entity reference (ROCrateEntity) with a ``contentUrl``
      or an ``@id`` that is itself a download URL
    """
    if isinstance(dist, str):
        return dist if dist.startswith("http") else None
    if hasattr(dist, "get_property"):
        # Prefer contentUrl, fall back to @id
        content_url_raw = dist.get_property("contentUrl")
        if content_url_raw:
            url = (content_url_raw if isinstance(content_url_raw, str)
                   else content_url_raw.id if hasattr(content_url_raw, "id") else None)
            if url and url.startswith("http"):
                return url
        if hasattr(dist, "id") and dist.id and dist.id.startswith("http"):
            return dist.id
    return None


@requirement(name="Dataset: distribution downloadability")
class DatasetDistributionChecker(PyFunctionCheck):
    """
    If a Dataset declares a ``distribution`` property pointing to a DataDownload
    entity, the referenced archive SHOULD be directly downloadable (RO-Crate 1.2,
    RECOMMENDED). Downloadability is verified via Signposting, Content-Type, and
    content negotiation.
    """

    @check(name="Dataset: distribution SHOULD be downloadable", severity=Severity.RECOMMENDED)
    def check_distribution_downloadable(self, context: ValidationContext) -> bool:
        if context.settings.skip_availability_check:
            return True
        if context.settings.metadata_only:
            return True
        result = True
        for entity in context.ro_crate.metadata.get_dataset_entities():
            distribution_raw = entity.get_property("distribution")
            if not distribution_raw:
                continue
            distributions = (distribution_raw
                             if isinstance(distribution_raw, list)
                             else [distribution_raw])
            for dist in distributions:
                url = _resolve_distribution_url(dist)
                if not url:
                    continue
                try:
                    dl = check_downloadable(url)
                    if not dl.is_downloadable:
                        msg = (
                            f"The distribution '{url}' of Dataset '{entity.id}' "
                            f"SHOULD be downloadable"
                        )
                        if dl.reason:
                            msg += f": {dl.reason}"
                        context.result.add_issue(msg, self)
                        result = False
                except Exception as e:
                    context.result.add_issue(
                        f"Error checking downloadability of distribution '{url}' "
                        f"for Dataset '{entity.id}': {e}", self)
                    result = False
                if not result and context.fail_fast:
                    return result
        return result
