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

"""Public re-exports for ``rocrate_validator.rocrate``.

The implementation is split across submodules grouped by responsibility:

* :mod:`.entity`   — :class:`ROCrateEntity` (RO-Crate JSON-LD entities)
* :mod:`.metadata` — :class:`ROCrateMetadata` (file descriptor wrapper)
* :mod:`.base`     — :class:`ROCrate` abstract base + factory
* :mod:`.plain`    — local folder / local zip / remote zip variants
* :mod:`.bagit`    — BagIt-wrapped variants

Callers should keep importing from ``rocrate_validator.rocrate`` as before;
this module re-exports every public name from the submodules.
"""

from .bagit import BagitROCrate, ROCrateBagitLocalFolder, ROCrateBagitLocalZip, ROCrateBagitRemoteZip
from .base import ROCrate
from .entity import ROCrateEntity
from .metadata import ROCrateMetadata
from .plain import ROCrateLocalFolder, ROCrateLocalZip, ROCrateRemoteZip

__all__ = [
    "BagitROCrate",
    "ROCrate",
    "ROCrateBagitLocalFolder",
    "ROCrateBagitLocalZip",
    "ROCrateBagitRemoteZip",
    "ROCrateEntity",
    "ROCrateLocalFolder",
    "ROCrateLocalZip",
    "ROCrateMetadata",
    "ROCrateRemoteZip",
]
