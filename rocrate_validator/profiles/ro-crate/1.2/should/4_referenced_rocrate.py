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
Network-aware refinement for Referenced RO-Crate `sdDatePublished` check.

The structural SHACL shape `ReferencedROCrateSdDatePublishedRecommended`
already warns when a referenced RO-Crate data entity with an absolute URI
@id omits both `identifier` and `sdDatePublished`.  RO-Crate 1.2 § 4.5
relaxes that obligation when the URI declares Signposting
`Link: rel="cite-as"` (which supplies a persistent citation surrogate).
This Python check performs the network-dependent refinement.
"""

from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.signposting import has_signposting_cite_as

logger = logging.getLogger(__name__)


@requirement(
    name="Referenced RO-Crate: Signposting cite-as refinement for sdDatePublished"
)
class ReferencedROCrateSignpostingCiteAsChecker(PyFunctionCheck):
    """
    Network-aware refinement of the `sdDatePublished` requirement for
    referenced RO-Crate data entities (RO-Crate 1.2, § 4.5).
    """

    @check(
        name="Referenced RO-Crate: `sdDatePublished` SHOULD be present when Signposting cite-as is not declared",
        severity=Severity.RECOMMENDED,
    )
    def check_sddatepublished_signposting(self, context: ValidationContext) -> bool:
        """
        For each referenced RO-Crate data entity whose @id is an absolute URI
        with no declared `identifier` and no `sdDatePublished`, verify whether
        the URI declares Signposting `Link: rel="cite-as"`.  If cite-as is
        absent the entity SHOULD include `sdDatePublished`.
        """
        if context.settings.skip_availability_check:
            return True
        if not (context.settings.creation_time or context.settings.enforce_availability):
            return True
        if context.settings.metadata_only:
            return True

        result = True
        try:
            root = context.ro_crate.metadata.get_root_data_entity()
        except Exception:
            return True

        for entity in context.ro_crate.metadata.get_dataset_entities():
            if entity.id == root.id:
                continue
            entity_id = entity.id
            if not (entity_id.startswith("http://") or entity_id.startswith("https://")):
                continue
            conforms_to = entity.get_property("conformsTo", [])
            if not isinstance(conforms_to, list):
                conforms_to = [conforms_to]
            conforms_to_ids = [c.id if hasattr(c, "id") else str(c) for c in conforms_to]
            if not any(c and c.startswith("https://w3id.org/ro/crate") for c in conforms_to_ids):
                continue
            if entity.get_property("identifier"):
                continue
            if entity.get_property("sdDatePublished"):
                continue

            cite_as_present = has_signposting_cite_as(entity_id)
            if cite_as_present is None:
                logger.debug(
                    "Signposting probe for referenced RO-Crate '%s' failed; "
                    "skipping cite-as refinement.",
                    entity_id,
                )
                continue
            if cite_as_present:
                logger.debug(
                    "Referenced RO-Crate '%s' declares Signposting rel='cite-as'; "
                    "`sdDatePublished` not required.",
                    entity_id,
                )
                continue

            context.result.add_issue(
                f"Referenced RO-Crate '{entity_id}' has no Signposting "
                f"`Link: rel=\"cite-as\"` declared; `sdDatePublished` SHOULD be "
                f"present to indicate when the absolute URI was accessed",
                self,
            )
            result = False
            if context.fail_fast:
                return result

        return result
