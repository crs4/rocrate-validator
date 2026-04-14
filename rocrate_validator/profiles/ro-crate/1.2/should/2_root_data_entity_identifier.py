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

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)
from rocrate_validator.utils import log as logging
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
