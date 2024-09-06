# Copyright (c) 2024 CRS4
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

import rocrate_validator.log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

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
        by a simple retrieval (e.g. HTTP GET) permitting redirection and HTTP/HTTPS URIs
        """
        result = True
        for entity in context.ro_crate.metadata.get_web_data_entities():
            assert entity.id is not None, "Entity has no @id"
            try:
                if not entity.is_available():
                    context.result.add_error(
                        f'Web-based Data Entity {entity.id} is not available', self)
                    result = False
            except Exception as e:
                context.result.add_error(
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
            if entity.is_available():
                content_size = entity.get_property("contentSize")
                if content_size and int(content_size) != context.ro_crate.get_external_file_size(entity.id):
                    context.result.add_check_issue(
                        f'The property contentSize={content_size} of the Web-based Data Entity '
                        f'{entity.id} does not match the actual size of '
                        f'the downloadable content, i.e., {entity.content_size} (bytes)', self,
                        focusNode=entity.id, resultPath='contentSize', value=content_size)
                    result = False
            if not result and context.fail_fast:
                return result
        return result
