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

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.signposting import check_downloadable

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Data Entity: REQUIRED resource availability")
class DataEntityRequiredChecker(PyFunctionCheck):
    """
    Resources corresponding to local Data Entities MUST be present in the RO-Crate payload
    """

    @check(name="Data Entity: REQUIRED resource availability")
    def check_availability(self, context: ValidationContext) -> bool:
        """
        Check the presence of the Data Entity in the RO-Crate
        """
        if context.ro_crate.is_detached():
            logger.debug("Skipping data entity payload checks for detached RO-Crate")
            return True
        # Skip the check in metadata-only mode
        if context.settings.metadata_only:
            logger.debug("Skipping file descriptor existence check in metadata-only mode")
            return True
        # Perform the check
        result = True
        for entity in context.ro_crate.metadata.get_data_entities(exclude_web_data_entities=True):
            assert entity.id is not None, "Entity has no @id"
            logger.debug("Ensure the presence of the Data Entity '%s' within the RO-Crate", entity.id)
            try:
                logger.debug("Ensure the presence of the Data Entity '%s' within the RO-Crate", entity.id)
                if entity.has_local_identifier():
                    logger.debug(
                        "Ignoring the Data Entity '%s' as it is a local entity with a local identifier. "
                        "According to the RO-Crate specification, local entities with local identifiers "
                        "are not required to be included in the RO-Crate payload"
                        "(see https://github.com/ResearchObject/ro-crate/issues/400#issuecomment-2779152885 and "
                        "https://github.com/ResearchObject/ro-crate/pull/426 for more details)",
                        entity.id)
                    continue
                if not entity.has_relative_path():
                    logger.debug(
                        "Ignoring the Data Entity '%s' as it is a local entity with an absolute path. "
                        "According to the RO-Crate specification, local entities with absolute paths "
                        "are not required to be included in the RO-Crate payload. "
                        "It is only recommended that they exist at the time of RO-Crate creation.",
                        entity.id)
                    continue
                if not entity.is_available():
                    context.result.add_issue(
                        f"The RO-Crate does not include the Data Entity '{entity.id}' as part of its payload", self)
                    result = False
            except Exception as e:
                context.result.add_issue(
                    f"Unable to check the the presence of the Data Entity '{entity.id}' within the RO-Crate", self)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(e, exc_info=True)
                result = False
            if not result and context.fail_fast:
                return result
        return result


@requirement(name="Detached RO-Crate: data entities MUST be web-based")
class DetachedDataEntityChecker(PyFunctionCheck):
    """
    In a detached RO-Crate, all Data Entities MUST be web-based
    resources (i.e., have an absolute URL as @id).
    """

    @check(name="Detached RO-Crate: data entities MUST be web-based")
    def check_detached_entities(self, context: ValidationContext) -> bool:
        if not context.ro_crate.is_detached():
            return True
        result = True
        root_entity_id = None
        try:
            root_entity_id = context.ro_crate.metadata.get_root_data_entity().id
        except Exception:
            pass
        for entity in context.ro_crate.metadata.get_data_entities():
            if root_entity_id and entity.id == root_entity_id:
                continue
            if not entity.is_remote():
                context.result.add_issue(
                    f"Data Entity '{entity.id}' is not web-based, "
                    f"but in a detached RO-Crate all Data Entities "
                    f"MUST have an absolute URL as @id", self)
                result = False
                if context.fail_fast:
                    return False
        return result


@requirement(name="Data Entity: identifier requirements")
class DataEntityIdentifierChecker(PyFunctionCheck):
    """
    Data Entity identifiers must be valid URI references and use relative paths for payload files.
    """

    @check(name="Data Entity: @id value requirements")
    def check_identifiers(self, context: ValidationContext) -> bool:
        result = True
        root_entity_id = None
        root_entity_is_local = False
        root_entity_absolute_path = None
        try:
            root_data_entity = context.ro_crate.metadata.get_root_data_entity()
            root_entity_id = root_data_entity.id
            root_entity_is_local = root_data_entity.id_as_uri.is_local_resource() if root_data_entity.id_as_uri else False
            root_entity_absolute_path = root_data_entity.id_as_path if root_data_entity.has_absolute_path() else None
        except Exception:
            pass
        for entity in context.ro_crate.metadata.get_data_entities():
            if root_entity_id and entity.id == root_entity_id:
                continue
            if not root_entity_is_local and not entity.is_remote():
                context.result.add_issue(
                    f"Data Entity '{entity.id}' has a local identifier but the Root Data Entity does not have a local identifier", self)
                result = False
                if context.fail_fast:
                    return False
            if entity.has_local_identifier():
                continue
            if "\\" in entity.id or " " in entity.id:
                context.result.add_issue(
                    f"Data Entity '{entity.id}' has an invalid @id; use URI-compatible paths", self)
                result = False
                if context.fail_fast:
                    return False
            if (root_entity_is_local and
                    not str(entity.id_as_path).startswith(str(root_entity_absolute_path))):
                if (root_entity_is_local and not str(entity.id).startswith("./") and (
                    str(entity.id).startswith("/") or
                    str(entity.id).startswith("file://")
                )):
                    context.result.add_issue(
                        f"Data Entity '{entity.id}' MUST use a relative @id within the RO-Crate root", self)
                    result = False
                    if context.fail_fast:
                        return False
        return result

    @check(name="Data Entity: relative @id for payload files")
    def check_relative_paths(self, context: ValidationContext) -> bool:
        if context.ro_crate.is_detached():
            return True
        result = True
        for entity in context.ro_crate.metadata.get_data_entities():
            if entity.has_local_identifier() or entity.is_remote():
                continue
            if entity.has_absolute_path():
                if context.ro_crate.has_file(entity.id_as_path) or context.ro_crate.has_directory(entity.id_as_path):
                    context.result.add_issue(
                        f"Data Entity '{entity.id}' should use a relative @id within the RO-Crate root", self)
                    result = False
                    if context.fail_fast:
                        return False
        return result


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
    Web-based Data Entities MUST be directly downloadable at the time of creation
    (RO-Crate 1.2). Downloadability is verified via Signposting (rel=item,
    rel=describedby), direct Content-Type inspection, and content negotiation.
    """

    @check(name="Web-based Data Entity: REQUIRED resource availability")
    def check_availability(self, context: ValidationContext) -> bool:
        if context.settings.skip_availability_check:
            return True
        if not (context.settings.creation_time or context.settings.enforce_availability):
            return True
        if context.settings.metadata_only:
            return True
        result = True
        for entity in context.ro_crate.metadata.get_web_data_entities():
            assert entity.id is not None, "Entity has no @id"
            # Skip directory URIs: assumed available, not directly downloadable by spec
            if entity.id.endswith("/"):
                logger.debug("Skipping downloadability check for directory entity '%s'", entity.id)
                continue
            try:
                dl = check_downloadable(entity.id)
                if not dl.is_downloadable:
                    msg = f"Web-based Data Entity '{entity.id}' is not directly downloadable"
                    if dl.reason and "HTML" in dl.reason:
                        msg = (
                            f"Web-based Data Entity '{entity.id}' references an HTML page "
                            f"(possible splash page or viewer application); "
                            f"it MUST be directly downloadable"
                        )
                    elif dl.reason:
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
            try:
                if not entity.is_available():
                    context.result.add_issue(
                        f"Web-based Data Entity '{entity.id}' is not directly downloadable", self)
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
                    if content_int is not None and content_int != external_size:
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
                try:
                    url_value = url if isinstance(url, str) else url.id
                    if not context.ro_crate.get_external_file_size(url_value):
                        context.result.add_issue(
                            f"contentUrl {url_value} for Web-based Data Entity {entity.id} is not directly downloadable",
                            self)
                        result = False
                except Exception as e:
                    context.result.add_issue(
                        f"contentUrl {url} for Web-based Data Entity {entity.id} is not directly downloadable: {e}",
                        self)
                    result = False
                if not result and context.fail_fast:
                    return result
        return result
