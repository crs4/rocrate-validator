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

import re
import zipfile
from abc import ABC
from pathlib import Path
from urllib.parse import unquote

from rocrate_validator.constants import HTTP_STATUS_OK
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.uri import URI

from .base import ROCrate
from .plain import ROCrateLocalFolder, ROCrateLocalZip, ROCrateRemoteZip

# set up logging
logger = logging.getLogger(__name__)


class BagitROCrate(ROCrate, ABC):
    def __init__(self, uri, relative_root_path=None):
        super().__init__(uri, relative_root_path)

        # check if the path is a BagIt-wrapped crate
        assert self.is_bagit_wrapping_crate(uri), "Not a BagIt-wrapped RO-Crate"

    @staticmethod
    def is_bagit_wrapping_crate(uri: str | Path | URI) -> bool:
        """
        Check if the RO-Crate is a BagIt-wrapped crate.

        :param uri: the URI of the RO-Crate
        :type uri: Union[str, Path, URI]

        :return: `True` if the RO-Crate is a BagIt-wrapped crate, `False` otherwise
        :rtype: bool
        """
        if not isinstance(uri, URI):
            uri = URI(uri)

        result = False
        try:
            # Check for local directory
            if uri.is_local_directory():
                base_path = uri.as_path()
                result = (base_path / "bagit.txt").is_file() and (
                    base_path / "data" / "ro-crate-metadata.json"
                ).is_file()

            # Check for local zip file
            elif uri.is_local_file():
                path = uri.as_path()
                if path.suffix == ".zip":
                    with zipfile.ZipFile(path, "r") as zf:
                        namelist = zf.namelist()
                        result = "bagit.txt" in namelist and "data/ro-crate-metadata.json" in namelist

            # Check for remote zip file
            elif uri.is_remote_resource():
                # For remote resources, we need to check if both files exist
                # We'll use HTTP HEAD requests to check without downloading
                base_url = str(uri).rstrip("/")

                if not base_url.endswith(".zip"):
                    # Check for bagit.txt
                    bagit_response = HttpRequester().head(f"{base_url}/bagit.txt")
                    if bagit_response.status_code == HTTP_STATUS_OK:
                        # Check for data/ro-crate-metadata.json
                        metadata_response = HttpRequester().head(f"{base_url}/data/ro-crate-metadata.json")
                        result = metadata_response.status_code == HTTP_STATUS_OK
                else:
                    # If it's a remote zip file, we need to download it partially
                    # Temporarily create instance to check
                    temp_crate = ROCrateRemoteZip(uri)
                    logger.debug("Initializing ROCrateRemoteZip for URI: %s", uri)
                    has_bagit_txt = temp_crate.has_file(Path("bagit.txt"))
                    logger.debug("Presence of 'bagit.txt': %s", has_bagit_txt)
                    has_ro_crate_metadata = temp_crate.has_file(Path("data/ro-crate-metadata.json"))
                    logger.debug("Presence of 'data/ro-crate-metadata.json': %s", has_ro_crate_metadata)
                    result = has_bagit_txt and has_ro_crate_metadata
                    del temp_crate
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error loading remote BagIt RO-Crate metadata")
        return result

    def __check_search_path__(self, path):
        """
        Check if the search path is valid for a BagIt-wrapped RO-Crate,
        i.e., if it points to the 'data/' directory.

        :param path: the path to resolve
        :type path: Path
        :return: the search path if valid, None otherwise
        :rtype: Path or None
        """
        search_path, root_path = super().__get_search_path__(path)
        # Check if the path has the substring 'data/' in it
        has_sub_data_path = re.search(r"data/", str(search_path))
        logger.debug(
            "The search path '%s' %s the 'data/' sub-path",
            search_path,
            "contains" if has_sub_data_path else "does not contain",
        )
        if search_path == "." or not has_sub_data_path:
            return search_path, root_path
        return None, None


class ROCrateBagitLocalFolder(BagitROCrate, ROCrateLocalFolder):
    def __init__(self, uri: str | Path | URI, relative_root_path: Path | None = None):
        # initialize the parent classes
        super(ROCrateLocalFolder, self).__init__(uri, relative_root_path=relative_root_path)
        # check if the path is a BagIt-wrapped crate
        assert self.is_bagit_wrapping_crate(uri), "Not a BagIt-wrapped RO-Crate"

    def __parse_path__(self, path: Path) -> Path:
        search_path, root_path = self.__check_search_path__(path)
        # if search_path and root_path are set, adjust the path
        if search_path and root_path:
            path = root_path / Path("data") / search_path
            if not path.exists():
                path = Path(unquote(str(path)))
        return path


class ROCrateBagitLocalZip(BagitROCrate, ROCrateLocalZip):
    """
    Class representing an RO-Crate stored in a local BagIt-wrapped zip file.
    """

    def __parse_path__(self, path: Path) -> Path:
        # Extract the search path relative to the root of the RO-Crate root path
        search_path, _ = super().__check_search_path__(path)

        # if search_path is set, adjust the path
        if search_path:
            path = Path("data") / search_path
            assert self._zipref is not None, "Zip reference not initialized"
            zip_namelist = self._zipref.namelist()
            if str(path) not in zip_namelist and f"{path}/" not in zip_namelist:
                path = Path(unquote(str(path)))
        return path


class ROCrateBagitRemoteZip(ROCrateBagitLocalZip, ROCrateRemoteZip):
    pass
