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
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.uri import AvailabilityStatus

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Web-based Data Entity: RECOMMENDED resource availability")
class WebDataEntityRecommendedChecker(PyFunctionCheck):
    """
    Web-based Data Entity instances SHOULD be available
    at the URIs specified in the `@id` property of the Web-based Data Entity.
    """

    @check(name="Web-based Data Entity: resource availability")
    def check_availability(self, context: ValidationContext) -> bool:
        """
        Check if the Web-based Data Entity is directly downloadable
        by a simple retrieval (e.g. HTTP GET) permitting redirection and HTTP/HTTPS URIs.

        Resources that cannot be natively retrieved by the validator (e.g.
        `scp://`, `s3://`, `sftp://`) or that are protected by an authorization
        mechanism (HTTP 401/403) are reported as recommendation-level issues
        and logged as warnings, without invalidating the validation.
        """
        result = True
        for entity in context.ro_crate.metadata.get_web_data_entities():
            assert entity.id is not None, "Entity has no @id"
            try:
                status = entity.check_availability()
                if status == AvailabilityStatus.AVAILABLE:
                    continue
                if status == AvailabilityStatus.UNAUTHORIZED:
                    msg = (
                        f"Web-based Data Entity {entity.id} is protected by an "
                        f"authorization mechanism; availability could not be verified"
                    )
                    logger.warning(msg)
                    context.result.add_issue(msg, self)
                elif status == AvailabilityStatus.UNCHECKABLE:
                    scheme = entity.id_as_uri.scheme
                    msg = (
                        f"Web-based Data Entity {entity.id} uses scheme "
                        f"'{scheme}' which is not natively supported by the "
                        f"validator; availability could not be verified"
                    )
                    logger.warning(msg)
                    context.result.add_issue(msg, self)
                else:
                    context.result.add_issue(
                        f'Web-based Data Entity {entity.id} is not available', self)
                    result = False
            except Exception as e:
                context.result.add_issue(
                    f'Web-based Data Entity {entity.id} is not available: {e}', self)
                result = False
            if not result and context.fail_fast:
                return result
        return result

    @check(name="Web-based Data Entity: `contentSize` property")
    def check_content_size(self, context: ValidationContext) -> bool:
        """
        Check if the Web-based Data Entity has a `contentSize` property
        and if it is set to actual size of the downloadable content
        """
        result = True
        for entity in context.ro_crate.metadata.get_web_data_entities():
            assert entity.id is not None, "Entity has no @id"
            # Skip entities whose scheme the validator cannot natively fetch
            # (e.g. scp://, s3://): without retrieving the content there is
            # no actual size to compare `contentSize` against. Reachability
            # is then checked separately via `is_available()` below.
            if not entity.id_as_uri.is_natively_checkable():
                continue
            if entity.is_available():
                content_size = entity.get_property("contentSize")
                actual_size = context.ro_crate.get_external_file_size(entity.id)
                if content_size and int(content_size) != actual_size:
                    context.result.add_issue(
                        f'The property contentSize={content_size} of the Web-based Data Entity '
                        f'{entity.id} does not match the actual size of '
                        f'the downloadable content, i.e., {actual_size} (bytes)', self,
                        violatingEntity=entity.id, violatingProperty='contentSize', violatingPropertyValue=content_size)
                    result = False
            if not result and context.fail_fast:
                return result
        return result
