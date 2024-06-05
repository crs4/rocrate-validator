import http
import json
import urllib.request
from typing import Optional

import requests

import rocrate_validator.log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


class WebDataEntity:

    def __init__(self, entity: dict):
        self._data = entity
        self._remote_site = None
        self._download_exception = None

    @property
    def data(self) -> dict:
        return self._data.copy()

    @property
    def id(self) -> str:
        return self._data.get("@id", "")

    def get_property(self,  property_name: str) -> dict:
        return self._data.get(property_name, None)

    def is_web_data_entity(self) -> bool:
        return self._data.get("@id", "").startswith(("http", "https"))

    def is_ftp_data_entity(self) -> bool:
        return self._data.get("@id", "").startswith(("ftp", "ftps"))

    @property
    def remote_resource(self) -> http.client.HTTPResponse:
        if not self._remote_site:
            self._remote_site = urllib.request.urlopen(self.id)
        return self._remote_site

    @property
    def content_size(self) -> Optional[int]:
        r = self.remote_resource
        if not r:
            return -1
        try:
            return int(r.info().get('Content-Length'))
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return -1

    def is_downloadable(self, silent: bool = True) -> bool:
        if not self.is_web_data_entity():
            return False
        # if self.is_ftp_data_entity() and not self._data.get("@id", "").startswith(("ftp://", "ftps://")):
        #     return False
        try:
            remote = self.remote_resource
            return remote and remote.status == 200
        except Exception as e:
            logger.exception(e)
            # if not silent raise the exception
            if not silent:
                raise e
            return False


@requirement(name="Web Data Entity: RECOMMENDED resource availability")
class WebDataEntityRecommendedChecker(PyFunctionCheck):
    """
    Web Data Entity instances SHOULD be available at the URIs specified in the `@id` property of the Web Data Entity.
    """

    _json_dict_cache: Optional[dict] = None
    _resources_cache: dict[str, requests.Response] = {}

    def get_json_dict(self, context: ValidationContext) -> dict:
        if self._json_dict_cache is None or \
                self._json_dict_cache['file_descriptor_path'] != context.file_descriptor_path:
            # invalid cache
            try:
                with open(context.file_descriptor_path, "r") as file:
                    self._json_dict_cache = dict(
                        json=json.load(file),
                        file_descriptor_path=context.file_descriptor_path)
            except Exception as e:
                context.result.add_error(
                    f'file descriptor "{context.rel_fd_path}" is not in the correct format', self)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
                return {}
        return self._json_dict_cache['json']

    def find_entity(self, context: ValidationContext, entity_id: str) -> dict:
        json_dict = self.get_json_dict(context)
        for entity in json_dict["@graph"]:
            if entity["@id"] == entity_id:
                return entity
        return {}

    def find_property(self, context: ValidationContext, entity_id: str, property_name: str) -> dict:
        entity = self.find_entity(context, entity_id)
        if entity:
            return entity.get(property_name, {})
        return {}

    def get_web_data_entities(self, context: ValidationContext) -> list[WebDataEntity]:
        json_dict = self.get_json_dict(context)
        web_data_entities = []
        for entity in json_dict["@graph"]:
            entity_id = entity.get("@id", None)
            entity_type = entity.get("@type", None)
            # Skip entity if it is not a File
            if isinstance(entity_type, list):
                if not "File" in entity_type:
                    continue
            if not "File" in entity_type:
                continue
            if entity_id is not None and entity_id.startswith(("http", "https")):
                web_data_entities.append(WebDataEntity(entity))
        return web_data_entities

    @check(name="Web Data Entity availability")
    def check_availability(self, context: ValidationContext) -> bool:
        """
        Check if the Web Data Entity is directly downloadable 
        by a simple retrieval (e.g. HTTP GET) permitting redirection and HTTP/HTTPS URIs
        """
        result = True
        for entity in self.get_web_data_entities(context):
            assert entity.id is not None, "Entity has no @id"
            logger.error("Is a web data entity")
            try:
                if not entity.is_downloadable(silent=False):
                    response = entity.remote_resource
                    if response is None:
                        context.result.add_error(
                            f'Web Data Entity {entity.id} is not available', self)
                        result = False
                    elif response.status != 200:
                        context.result.add_error(
                            f'Web Data Entity {entity.id} is not available (HTTP {response.status_code})', self)
                        result = False
            except Exception as e:
                context.result.add_error(
                    f'Web Data Entity {entity.id} is not available: {e}', self)
                result = False
            if not result and context.fail_fast:
                return result
        return result

    @check(name="Web Data Entity: `contentSize` property")
    def check_content_size(self, context: ValidationContext) -> bool:
        """
        Check if the Web Data Entity has a `contentSize` property
        and if it is set to actual size of the downloadable content
        """
        result = True
        for entity in self.get_web_data_entities(context):
            assert entity.id is not None, "Entity has no @id"
            if entity.is_downloadable():
                content_size = entity.get_property("contentSize")
                if content_size and int(content_size) != entity.content_size:
                    context.result.add_check_issue(
                        f'The property contentSize={content_size} of the Web Data Entity {entity.id} does not match the actual size of '
                        f'the downloadable content, i.e., {entity.content_size} (bytes)', self,
                        focusNode=entity.id, resultPath='contentSize', value=content_size)
                    result = False
            if not result and context.fail_fast:
                return result

        return result
