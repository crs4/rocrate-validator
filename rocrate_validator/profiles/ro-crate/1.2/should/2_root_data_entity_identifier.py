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
from rocrate_validator.utils.uri import URI

logger = logging.getLogger(__name__)


@requirement(name="Root Data Entity: RECOMMENDED identifier")
class DetachedROCrateRootDataEntityIdentifierChecker(PyFunctionCheck):
    """
    In a detached RO-Crate, the Root Data Entity @id SHOULD be an absolute URI.
    """

    @check(name="Root Data Entity: RECOMMENDED identifier")
    def check_identifier(self, context: ValidationContext) -> bool:
        """
        In a detached RO-Crate, the Root Data Entity @id SHOULD be an absolute URI.
        """
        try:
            if not context.ro_crate.is_detached():
                return True
            root_entity = context.ro_crate.metadata.get_root_data_entity()
            if not root_entity.is_remote():
                return True

            if root_entity.id == './':
                context.result.add_issue(
                    'In a remote RO-Crate, the Root Data Entity @id SHOULD be an absolute URL, not `./`', self)
                return False
            if not URI(root_entity.id).is_remote_resource():
                context.result.add_issue(
                    'In a remote RO-Crate, the Root Data Entity @id SHOULD be an absolute URL', self)
                return False

            return True
        except Exception as e:
            context.result.add_issue(
                f'Error checking Root Data Entity @id: {str(e)}', self)
            return False


@requirement(name="Root Data Entity: use cite-as for resolvable identifiers")
class RootDataEntityCiteAsIdentifierChecker(PyFunctionCheck):
    """
    If the Root Data Entity has a resolvable identifier, it SHOULD be included in the `cite-as` property of the RO-Crate Metadata Entity.
    """

    @check(name="Root Data Entity: use cite-as for resolvable identifiers")
    def check_cite_as_reference(self, context: ValidationContext) -> bool:
        """
        If the Root Data Entity has a resolvable identifier,
        it SHOULD be included in the `cite-as` property of the RO-Crate Metadata Entity.
        """
        try:
            if not context.ro_crate.is_detached():
                return True
            root_entity = context.ro_crate.metadata.get_root_data_entity()
            if not root_entity.is_remote():
                return True

            # Check if the `cite-as` property is present and references the Root Data Entity
            cite_as = root_entity.get_property('cite-as')
            if root_entity.id_as_uri.is_remote_resource():
                if not cite_as:
                    context.result.add_issue(
                        'If the Root Data Entity has a resolvable identifier, '
                        'it SHOULD be included in the `cite-as` property of the RO-Crate Metadata Entity.', self)
                    return False

            # If the `cite-as` property is present, check that it references the Root Data Entity
            if cite_as.id != root_entity.id:
                context.result.add_issue(
                    'If the Root Data Entity has a resolvable identifier, '
                    'it SHOULD be included in the `cite-as` property of the RO-Crate Metadata Entity.', self)
                return False

            return True
        except Exception as e:
            context.result.add_issue(
                f'Error checking Root Data Entity `cite-as` reference: {str(e)}', self)
            return False


def _extract_identifier_urls(identifier_raw) -> list[str]:
    """
    Extract HTTP URL(s) from a raw ``identifier`` property value.

    The identifier can be:
    - A plain string URL
    - A ``schema:PropertyValue`` entity with a ``url`` or ``value`` sub-property
    - A list of any of the above
    """
    urls = []
    items = identifier_raw if isinstance(identifier_raw, list) else [identifier_raw]
    for item in items:
        if isinstance(item, str):
            if item.startswith("http"):
                urls.append(item)
        elif hasattr(item, "get_property"):
            # PropertyValue: try url first, then value
            for prop in ("url", "value"):
                val = item.get_property(prop)
                if val:
                    url = val if isinstance(val, str) else val.id if hasattr(val, "id") else None
                    if url and url.startswith("http"):
                        urls.append(url)
                        break
        elif hasattr(item, "id") and item.id and item.id.startswith("http"):
            urls.append(item.id)
    return urls


@requirement(name="Root Data Entity: persistent identifier resolution")
class RootDataEntityPersistentIdentifierChecker(PyFunctionCheck):
    """
    If the Root Data Entity has an ``identifier`` property with a resolvable
    HTTP URL, resolving that URL SHOULD ultimately provide the RO-Crate Metadata
    Document or an archive, accessible via Signposting or content negotiation
    (RO-Crate 1.2, RECOMMENDED).
    """

    @check(name="Root Data Entity: identifier SHOULD resolve to RO-Crate content",
           severity=Severity.RECOMMENDED)
    def check_identifier_resolvable(self, context: ValidationContext) -> bool:
        if context.settings.skip_availability_check:
            return True
        if context.settings.metadata_only:
            return True
        try:
            root_entity = context.ro_crate.metadata.get_root_data_entity()
            identifier_raw = root_entity.get_property("identifier")
            if not identifier_raw:
                return True

            urls = _extract_identifier_urls(identifier_raw)
            if not urls:
                return True

            result = True
            for url in urls:
                dl = check_downloadable(url)
                if not dl.is_downloadable:
                    msg = (
                        f"The Root Data Entity identifier '{url}' SHOULD resolve to the "
                        f"RO-Crate Metadata Document or an archive via Signposting or "
                        f"content negotiation"
                    )
                    if dl.reason:
                        msg += f": {dl.reason}"
                    context.result.add_issue(msg, self)
                    result = False
            return result
        except Exception as e:
            context.result.add_issue(
                f"Error checking Root Data Entity identifier resolution: {str(e)}", self)
            return False
