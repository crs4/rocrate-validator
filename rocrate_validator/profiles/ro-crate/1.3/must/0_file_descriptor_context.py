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
from http import HTTPStatus
from typing import Any
from urllib.parse import urljoin

from rocrate_validator.errors import ROCrateMetadataNotFoundError
from rocrate_validator.models import CheckResult, CheckResultValue, ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester, OfflineCacheMissError

logger = logging.getLogger(__name__)

_HANDLED_ERRORS = (AssertionError, AttributeError, KeyError, TypeError, ValueError)


@requirement(name="File Descriptor JSON-LD format")
class FileDescriptorJsonLdContext(PyFunctionCheck):
    """Validate the RO-Crate 1.3 JSON-LD context reference."""

    def __get_remote_context__(self, context_uri: str) -> object:
        raw_data = HttpRequester().get(context_uri, headers={"Accept": "application/ld+json, application/json"})
        if raw_data.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Unable to retrieve the JSON-LD context '{context_uri}'")

        content_type = raw_data.headers.get("Content-Type", "")
        if "application/ld+json" not in content_type and "application/json" not in content_type:
            link_header = raw_data.headers.get("Link", "")
            match = re.search(r'<([^>]+)>;\s*rel="alternate";\s*type="application/(ld\+json|json)"', link_header)
            if not match:
                raise RuntimeError(f"Unable to retrieve the JSON-LD context from '{context_uri}'")
            alternate_url = match.group(1)
            if not alternate_url.startswith("http"):
                alternate_url = urljoin(context_uri, alternate_url)
            raw_data = HttpRequester().get(
                alternate_url,
                headers={"Accept": "application/ld+json, application/json"},
            )
            if raw_data.status_code != HTTPStatus.OK:
                raise RuntimeError(f"Unable to retrieve the JSON-LD context from alternate URL '{alternate_url}'")

        jsonld_context = raw_data.json()["@context"]
        assert isinstance(jsonld_context, dict)
        return jsonld_context

    def __check_remote_context__(self, context_uri: str) -> bool:
        try:
            return isinstance(self.__get_remote_context__(context_uri), dict)
        except OfflineCacheMissError:
            raise
        except (OSError, RuntimeError, *_HANDLED_ERRORS):
            logger.exception("Unexpected error during file descriptor context validation")
            return False

    def __check_contexts__(self, context: ValidationContext, jsonld_context: object) -> bool:
        is_valid = True
        if isinstance(jsonld_context, str) and not self.__check_remote_context__(jsonld_context):
            context.result.add_issue(f'Unable to retrieve the JSON-LD context "{jsonld_context}"', self)
            is_valid = False
        if isinstance(jsonld_context, list):
            for nested_context in jsonld_context:
                if not self.__check_contexts__(context, nested_context):
                    is_valid = False
        return is_valid

    @check(
        name="File Descriptor @context property validation",
        depends_on=("File Descriptor JSON format",),
    )
    def check_context(self, context: ValidationContext) -> CheckResultValue:
        """Require the RO-Crate 1.3 JSON-LD context and validate it."""
        expected_context = "https://w3id.org/ro/crate/1.3/context"
        try:
            json_dict: dict[str, Any] = context.ro_crate.metadata.as_dict()
            jsonld_context = json_dict.get("@context")
            if "@context" not in json_dict:
                context.result.add_issue(
                    f'RO-Crate file descriptor "{context.rel_fd_path}" does not contain a context', self
                )
                return False
            if not (
                jsonld_context == expected_context
                or (isinstance(jsonld_context, list) and expected_context in jsonld_context)
            ):
                context.result.add_issue(
                    f'RO-Crate file descriptor "{context.rel_fd_path}" '
                    f'does not reference the required context "{expected_context}"',
                    self,
                )
                return False
            return self.__check_contexts__(context, jsonld_context)
        except ROCrateMetadataNotFoundError:
            context.record_skip(self, "metadata descriptor is not available", "exception")
            return CheckResult.SKIPPED
        except UnicodeDecodeError:
            context.record_skip(self, "descriptor encoding check reported the failure", "exception")
            return CheckResult.SKIPPED
        except _HANDLED_ERRORS:
            logger.exception("Unexpected error during file descriptor context validation")
            return False
