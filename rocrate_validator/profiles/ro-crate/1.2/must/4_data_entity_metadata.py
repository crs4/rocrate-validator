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

import contextlib
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from rocrate_validator.errors import ROCrateMetadataNotFoundError
from rocrate_validator.models import CheckResult, CheckResultValue, ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.signposting import check_downloadable
from rocrate_validator.utils.uri import is_external_reference

# set up logging
logger = logging.getLogger(__name__)


def _data_entity_path_error(identifier: str) -> str | None:
    """
    Validate path forms without inferring transport or payload membership.

    This is not a general URI validator. RFC 8089 requires an absolute path
    after ``file:``, whereas RFC 3986 network-path references have an authority
    but no scheme. Neither a network-path reference nor a bare filesystem path
    expresses a path relative to the crate root.
    """
    if "\\" in identifier or " " in identifier:
        return "has an invalid @id; use URI-compatible paths"
    # Match the existing URI utility's drive-letter disambiguation on every OS.
    if re.match(r"^[A-Za-z]:/", identifier):
        return "has a Windows drive path; use a relative URI path or an absolute file URI"
    try:
        parsed = urlsplit(identifier)
    except ValueError:
        return "has an invalid @id; use a valid URI reference"
    if parsed.scheme == "file" and not parsed.path.startswith("/"):
        return "has an invalid @id; the file URI path MUST be absolute (RFC 8089 section 2)"
    path_error = None
    if not parsed.scheme:
        if identifier.startswith("//"):
            path_error = (
                "has a network-path reference; use an absolute URI with a scheme "
                "or a path relative to the RO-Crate root"
            )
        elif parsed.path.startswith("/"):
            path_error = "MUST use a relative @id within the RO-Crate root"
    return path_error


@requirement(name="Data Entity: REQUIRED resource availability")
class DataEntityRequiredChecker(PyFunctionCheck):
    """
    Resources corresponding to local Data Entities MUST be present in the RO-Crate payload
    """

    @check(name="Data Entity: REQUIRED resource availability")
    def check_availability(self, context: ValidationContext) -> CheckResultValue:  # noqa: C901
        """
        Check the presence of the Data Entity in the RO-Crate
        """
        try:
            is_detached = context.ro_crate.is_detached()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping Data Entity availability check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        if is_detached:
            logger.debug("Skipping data entity payload checks for detached RO-Crate")
            context.record_skip(self, "RO-Crate is detached", "returned")
            return CheckResult.SKIPPED
        # Skip the check in metadata-only mode
        if context.settings.metadata_only:
            logger.debug("Skipping file descriptor existence check in metadata-only mode")
            context.record_skip(self, "metadata-only mode", "configured")
            return CheckResult.SKIPPED
        # Perform the check
        result = True
        try:
            entities = context.ro_crate.metadata.get_data_entities(exclude_web_data_entities=True)
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping Data Entity availability check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        for entity in entities:
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
                        entity.id,
                    )
                    continue
                if is_external_reference(entity.id) or not entity.has_relative_path():
                    logger.debug(
                        "Ignoring the Data Entity '%s' as it is a local entity with an absolute path. "
                        "According to the RO-Crate specification, local entities with absolute paths "
                        "are not required to be included in the RO-Crate payload. "
                        "It is only recommended that they exist at the time of RO-Crate creation.",
                        entity.id,
                    )
                    continue
                if not entity.is_available():
                    context.result.add_issue(
                        f"The RO-Crate does not include the Data Entity '{entity.id}' as part of its payload", self
                    )
                    result = False
            except (AttributeError, OSError, TypeError, ValueError) as e:
                context.result.add_issue(
                    f"Unable to check the the presence of the Data Entity '{entity.id}' within the RO-Crate", self
                )
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
    def check_detached_entities(self, context: ValidationContext) -> CheckResultValue:
        try:
            is_detached = context.ro_crate.is_detached()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping detached Data Entity check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        if not is_detached:
            context.record_skip(self, "RO-Crate is attached", "returned")
            return CheckResult.SKIPPED
        result = True
        root_entity_id = None
        with contextlib.suppress(ValueError):
            root_entity_id = context.ro_crate.metadata.get_root_data_entity().id
        try:
            entities = context.ro_crate.metadata.get_data_entities()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping detached Data Entity check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        for entity in entities:
            if root_entity_id and entity.id == root_entity_id:
                continue
            if not is_external_reference(entity.id):
                context.result.add_issue(
                    f"Data Entity '{entity.id}' is not web-based, "
                    f"but in a detached RO-Crate all Data Entities "
                    f"MUST have an absolute URL as @id",
                    self,
                )
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
    def check_identifiers(self, context: ValidationContext) -> CheckResultValue:
        result = True
        root_entity_id = None
        root_entity_is_local = False
        with contextlib.suppress(ValueError):
            root_data_entity = context.ro_crate.metadata.get_root_data_entity()
            root_entity_id = root_data_entity.id
            root_entity_is_local = (
                root_data_entity.id_as_uri.is_local_resource() if root_data_entity.id_as_uri else False
            )
        try:
            entities = context.ro_crate.metadata.get_data_entities()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping Data Entity identifier check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        for entity in entities:
            if root_entity_id and entity.id == root_entity_id:
                continue
            if not root_entity_is_local and not is_external_reference(entity.id):
                context.result.add_issue(
                    f"Data Entity '{entity.id}' has a local identifier but the Root Data Entity "
                    "does not have a local identifier",
                    self,
                )
                result = False
                if context.fail_fast:
                    return False
            if entity.has_local_identifier():
                continue
            path_error = _data_entity_path_error(entity.id)
            if path_error:
                context.result.add_issue(f"Data Entity '{entity.id}' {path_error}", self)
                result = False
                if context.fail_fast:
                    return False
        return result

    @check(name="Data Entity: relative @id for payload files")
    def check_relative_paths(self, context: ValidationContext) -> CheckResultValue:
        try:
            is_detached = context.ro_crate.is_detached()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping relative Data Entity identifier check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        if is_detached:
            context.record_skip(self, "RO-Crate is detached", "returned")
            return CheckResult.SKIPPED
        result = True
        try:
            entities = context.ro_crate.metadata.get_data_entities()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping relative Data Entity identifier check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        for entity in entities:
            # This check only applies to attached crates with local filesystem
            # resources; local IDs and malformed paths are handled elsewhere.
            if (
                entity.has_local_identifier()
                or _data_entity_path_error(entity.id)
                or entity.is_remote()
                or not context.ro_crate.uri.is_local_resource()
            ):
                continue
            # An absolute file URI may identify an external local resource. Only
            # files actually inside the package must use a relative identifier.
            # Parse URI paths explicitly to handle file:/ and localhost, and
            # compare path components rather than textual prefixes.
            if not (is_external_reference(entity.id) or entity.has_absolute_path()):
                continue

            # URI paths are percent-encoded, so decode them before creating a
            # filesystem path. Non-file absolute paths already have a path form.
            parsed = urlsplit(entity.id)
            path = Path(unquote(parsed.path)) if parsed.scheme == "file" else entity.id_as_path
            # Resolve both paths before comparing them; this also follows symlinks,
            # so containment is evaluated against their canonical filesystem targets.
            root_path = context.ro_crate.uri.as_path().resolve()
            path = path.resolve()
            if not path.is_relative_to(root_path):
                continue

            # An absolute path inside the root is only subject to this rule if
            # it resolves to an actual file or directory in the crate payload.
            payload_path = path.relative_to(root_path)
            if not (context.ro_crate.has_file(payload_path) or context.ro_crate.has_directory(payload_path)):
                continue
            context.result.add_issue(
                f"Data Entity '{entity.id}' MUST use a relative @id within the RO-Crate root", self
            )
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
    def check_citation(self, context: ValidationContext) -> CheckResultValue:
        result = True
        try:
            entities = context.ro_crate.metadata.get_data_entities()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping Data Entity citation check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        for entity in entities:
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
                        f"Citation for Data Entity '{entity.id}' must reference a publication @id", self
                    )
                    result = False
                    if context.fail_fast:
                        return False
                    continue
                if not re.match(r"^[A-Za-z][A-Za-z0-9+\.-]*:", citation_id):
                    context.result.add_issue(f"Citation for Data Entity '{entity.id}' must be an absolute URI", self)
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

    @staticmethod
    def _not_downloadable_message(entity_id: str, dl) -> str:
        """Build the issue message for a web-based Data Entity that is not directly downloadable."""
        if dl.reason and "HTML" in dl.reason:
            return (
                f"Web-based Data Entity '{entity_id}' references an HTML page "
                f"(possible splash page or viewer application); "
                f"it MUST be directly downloadable"
            )
        msg = f"Web-based Data Entity '{entity_id}' is not directly downloadable"
        if dl.reason:
            msg += f": {dl.reason}"
        return msg

    @check(name="Web-based Data Entity: REQUIRED resource availability")
    def check_availability(self, context: ValidationContext) -> CheckResultValue:
        if (
            context.settings.skip_availability_check
            or not (context.settings.creation_time or context.settings.enforce_availability)
            or context.settings.metadata_only
        ):
            context.record_skip(self, "availability check is disabled or not requested", "configured")
            return CheckResult.SKIPPED
        result = True
        try:
            entities = context.ro_crate.metadata.get_web_data_entities()
        except ROCrateMetadataNotFoundError:
            logger.debug("Skipping web-based Data Entity availability check: metadata descriptor is not available")
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        for entity in entities:
            assert entity.id is not None, "Entity has no @id"
            # Skip directory URIs: assumed available, not directly downloadable by spec
            if entity.id.endswith("/"):
                logger.debug("Skipping downloadability check for directory entity '%s'", entity.id)
                continue
            try:
                dl = check_downloadable(entity.id)
                if not dl.is_downloadable:
                    context.result.add_issue(self._not_downloadable_message(entity.id, dl), self)
                    result = False
            except (OSError, RuntimeError, TypeError, ValueError) as e:
                context.result.add_issue(f"Web-based Data Entity '{entity.id}' availability check failed: {e}", self)
                result = False
            if not result and context.fail_fast:
                return result
        return result
