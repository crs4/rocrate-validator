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

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote

from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.uri import URI, AvailabilityStatus, is_external_reference

if TYPE_CHECKING:
    from .base import ROCrate
    from .metadata import ROCrateMetadata

# set up logging
logger = logging.getLogger(__name__)


class ROCrateEntity:
    def __init__(self, metadata: ROCrateMetadata, raw_data: dict) -> None:
        self._raw_data: dict = raw_data
        self._metadata = metadata

    @property
    def id(self) -> str:
        return cast("str", self._raw_data.get("@id"))

    @property
    def type(self) -> str | list[str]:
        return cast("str | list[str]", self._raw_data.get("@type"))

    def is_dataset(self) -> bool:
        return self.has_type("Dataset")

    def is_file(self) -> bool:
        return self.has_type("File")

    @property
    def name(self) -> str:
        return cast("str", self._raw_data.get("name"))

    @property
    def metadata(self) -> ROCrateMetadata:
        return self._metadata

    @property
    def ro_crate(self) -> ROCrate:
        return self.metadata.ro_crate

    def is_remote(self) -> bool:
        return self.id_as_uri.is_remote_resource()

    @classmethod
    def get_id_as_path(cls, entity_id: str, ro_crate: ROCrate | None = None) -> Path:
        return cls.get_path_from_identifier(
            entity_id,
            ro_crate.uri.as_path() if ro_crate and ro_crate.uri.is_local_resource() else None,
        )

    @staticmethod
    def get_path_from_identifier(
        identifier: str,
        rocrate_path: str | Path | None = None,
        decode: bool = False,
    ) -> Path:
        """
        Get the path from an identifier.

        :param identifier: the identifier of the entity
        :type identifier: str

        :param rocrate_path: the path to the RO-Crate
        :type rocrate_path: Optional[Union[str, Path]

        :return: the path to the entity
        :rtype: Path

        """

        def __define_path__(path: str, decode: bool = False) -> Path:
            # ensure the path is a string and remove the file:// prefix
            path = str(path).replace("file://", "")
            # Decode the path if required
            if decode:
                path = unquote(path)
            # Convert the path to a Path object
            path_obj = Path(path)
            # if the path is absolute, return it
            if path_obj.is_absolute():
                return path_obj
            # set the base path
            base_path: Path
            if rocrate_path is None:
                base_path = Path("./")
            elif not isinstance(rocrate_path, Path):
                base_path = Path(rocrate_path)
            else:
                base_path = rocrate_path
            try:
                # Check if the path if the root of the RO-Crate
                if path_obj == Path("./"):
                    return base_path
                # if the path is relative, try to resolve it
                return base_path / path_obj.relative_to(base_path)
            except ValueError:
                # if the path cannot be resolved, return the absolute path
                return base_path / path_obj

        # Define the path based on the identifier
        path = __define_path__(identifier, decode=decode)
        logger.debug("Defined path '%s' from identifier '%s'", path, identifier)
        return path

    @property
    def id_as_path(self) -> Path:
        return self.get_id_as_path(self.id, self.ro_crate)

    @classmethod
    def get_id_as_uri(cls, entity_id: str, ro_crate: ROCrate) -> URI:
        assert entity_id, "Entity ID cannot be None"
        # Per RO-Crate 1.1 § 4.2.2, an `@id` is either a relative URI path or
        # an external URI/IRI (RFC 3986/3987). External references are used
        # as-is (without resolving them against the crate URI) so the entity
        # is classified as remote/web-based; this covers both authority-based
        # forms (``http://``, ``scp://``) and scheme-only ones (``urn:``,
        # ``doi:``, ``arcp:``).
        if is_external_reference(entity_id):
            return URI(entity_id)
        # Otherwise the `@id` is a relative path: if the RO-Crate itself is
        # remote, resolve it against the crate URI so the entity is still
        # classified as remote/web-based.
        if ro_crate.uri.is_remote_resource() and entity_id.startswith("./"):
            return URI(f"{ro_crate.uri}/{entity_id[2:]}")
        return URI(cls.get_id_as_path(entity_id, ro_crate))

    @property
    def id_as_uri(self) -> URI:
        return self.get_id_as_uri(self.id, self.ro_crate)

    def has_absolute_path(self) -> bool:
        return self.get_id_as_path(self.id).is_absolute()

    def has_relative_path(self) -> bool:
        return not self.has_absolute_path()

    def has_local_identifier(self) -> bool:
        has_local_id = (
            self.id.startswith("#") or f"{self.ro_crate.uri}/#" in self.id or f"file://{self.ro_crate.uri}/#" in self.id
        )
        logger.debug(
            "Identifier '%s' is %s a local identifier",
            self.id,
            "" if has_local_id else " not",
        )
        return has_local_id

    def has_type(self, entity_type: str) -> bool:
        assert isinstance(entity_type, str), "Entity type must be a string"
        e_types = self.type if isinstance(self.type, list) else [self.type]
        return entity_type in e_types

    def has_types(self, entity_types: list[str], all_types: bool = False) -> bool:
        """
        Check if the entity has any or all of the specified types.
        """
        assert isinstance(entity_types, list), "Entity types must be a list"
        e_types = self.type if isinstance(self.type, list) else [self.type]
        if all_types:
            return all(t in e_types for t in entity_types)
        return any(t in e_types for t in entity_types)

    def __process_property__(self, _name: str, data: object) -> object:
        if isinstance(data, dict) and "@id" in data:
            entity = self.metadata.get_entity(data["@id"])
            if entity is None:
                return ROCrateEntity(self.metadata, data)
            return entity
        return data

    def get_property(self, name: str, default=None) -> Any:
        data = self._raw_data.get(name, default)
        if data is None:
            return None
        if isinstance(data, list):
            return [self.__process_property__(name, _) for _ in data]
        return self.__process_property__(name, data)

    @property
    def raw_data(self) -> object:
        return self._raw_data

    def is_local(self) -> bool:
        return not self.is_remote()

    def _check_local_availability(self) -> AvailabilityStatus:
        # Lazy import to avoid a runtime cycle: plain.py inherits from base.py,
        # which already depends on this module via ROCrateEntity.
        from .plain import ROCrateLocalFolder, ROCrateLocalZip  # noqa: PLC0415

        if self.ro_crate.uri.is_local_resource():
            if isinstance(self.ro_crate, ROCrateLocalFolder):
                found = self.ro_crate.has_file(self.id_as_path) or self.ro_crate.has_directory(self.id_as_path)
                return AvailabilityStatus.AVAILABLE if found else AvailabilityStatus.UNAVAILABLE
            if isinstance(self.ro_crate, ROCrateLocalZip):
                if self.id == "./":
                    return AvailabilityStatus.AVAILABLE
                found = self.ro_crate.has_directory(Path(unquote(str(self.id)))) or self.ro_crate.has_file(
                    Path(unquote(str(self.id)))
                )
                return AvailabilityStatus.AVAILABLE if found else AvailabilityStatus.UNAVAILABLE

        if self.ro_crate.uri.is_remote_resource():
            if self.id == "./":
                found = self.ro_crate.get_file_size(self.id_as_path) > 0
            else:
                found = self.ro_crate.has_directory(Path(unquote(str(self.id)))) or self.ro_crate.has_file(
                    Path(unquote(str(self.id)))
                )
            return AvailabilityStatus.AVAILABLE if found else AvailabilityStatus.UNAVAILABLE

        raise ROCrateInvalidURIError(uri=self.id, message="Could not determine the availability of the entity")

    def check_availability(self) -> AvailabilityStatus:
        """
        Return a fine-grained availability status for this entity.

        This is the primary check; :meth:`is_available` is the boolean
        shortcut built on top of it. The status distinguishes definitely
        unavailable resources, auth-protected ones, and remote URIs whose
        scheme the validator cannot natively check (scp://, s3://, ...).
        """
        try:
            entity_uri = self.id_as_uri
            if entity_uri.is_natively_checkable():
                logger.debug("Checking the availability of a remote entity")
                return entity_uri.check_availability()

            if entity_uri.is_remote_resource():
                logger.debug(
                    "Cannot natively verify availability for entity '%s' (scheme '%s')",
                    self.id,
                    entity_uri.scheme,
                )
                return AvailabilityStatus.UNCHECKABLE

            return self._check_local_availability()
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error checking entity availability")
            return AvailabilityStatus.UNAVAILABLE

    def is_available(self) -> bool:
        return self.check_availability() == AvailabilityStatus.AVAILABLE

    def get_size(self) -> int:
        try:
            return self.metadata.ro_crate.get_file_size(Path(self.id))
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error getting entity file size")
            return 0

    def __str__(self) -> str:
        return f"Entity({self.id})"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ROCrateEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
