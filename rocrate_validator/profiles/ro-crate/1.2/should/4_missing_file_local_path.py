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

# NOTE: This check is implemented as a Python PyFunctionCheck rather than a
# SHACL shape because the core condition — "the file is not present in the
# RO-Crate payload" — requires filesystem access (i.e. checking whether a
# referenced local file actually exists on disk or inside a ZIP archive).
# SHACL cannot express conditions that depend on external state such as
# file availability.  A SHACL shape could only verify that `localPath` is
# present as a property, which would produce false positives on every local
# file that *is* present and therefore has no need for `localPath`.  By
# using a Python check we can combine graph inspection with filesystem
# availability checks and emit a warning only when a local file is missing
# *and* no `localPath` property is provided.
#
# Additionally, the spec states that a File entity MAY use a local identifier
# starting with "#" for files that are deliberately not present in the
# payload.  In that case `localPath` SHOULD be used to indicate where the
# file can be found.  This requires distinguishing "#" identifiers from
# regular relative paths, which SHACL cannot do.

from rocrate_validator.models import Severity, ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils import log as logging

logger = logging.getLogger(__name__)


@requirement(name="Data Entity: missing file SHOULD use localPath")
class MissingFileLocalPathChecker(PyFunctionCheck):
    """
    In an attached RO-Crate, when a File Data Entity references a local file
    that is not present in the RO-Crate payload, the entity SHOULD declare a
    ``localPath`` property to indicate where the file can be found locally.

    Additionally, a File Data Entity whose ``@id`` begins with ``#`` denotes a
    deliberately absent file; in that case ``localPath`` SHOULD also be
    declared to indicate where the file can be found when it exists.
    (RO-Crate 1.2 specification, section on File Data Entities.)
    """

    @check(name="Missing local File SHOULD use localPath",
           severity=Severity.RECOMMENDED)
    def check_missing_file_local_path(self, context: ValidationContext) -> bool:
        if context.ro_crate.is_detached():
            return True
        if context.settings.metadata_only:
            return True
        root_entity_id = None
        try:
            root_entity_id = context.ro_crate.metadata.get_root_data_entity().id
        except Exception:
            pass
        result = True
        for entity in context.ro_crate.metadata.get_data_entities(
                exclude_web_data_entities=True):
            if root_entity_id and entity.id == root_entity_id:
                continue
            if not entity.is_file():
                continue
            if entity.has_local_identifier():
                local_path = entity.get_property("localPath")
                if not local_path:
                    context.result.add_issue(
                        f"File Data Entity '{entity.id}' uses a local "
                        f"identifier (#) for a deliberately absent file, "
                        f"but does not declare a `localPath` property; "
                        f"consider adding `localPath` to indicate where "
                        f"the file can be found locally",
                        self)
                    result = False
                    if context.fail_fast:
                        return False
                else:
                    local_path_value = (
                        local_path if isinstance(local_path, str)
                        else local_path.id if hasattr(local_path, "id")
                        else str(local_path)
                    )
                    logger.warning(
                        "File Data Entity '%s' declares localPath='%s' for a "
                        "deliberately absent file; the availability of this "
                        "path cannot be verified by the validator",
                        entity.id, local_path_value)
                continue
            if not entity.has_relative_path():
                continue
            if entity.is_available():
                continue
            local_path = entity.get_property("localPath")
            if not local_path:
                context.result.add_issue(
                    f"File Data Entity '{entity.id}' is not present in the "
                    f"RO-Crate payload and does not declare a `localPath` "
                    f"property; consider adding `localPath` to indicate where "
                    f"the file can be found locally",
                    self)
                result = False
                if context.fail_fast:
                    return False
        return result
