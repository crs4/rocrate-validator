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

"""Discovery of graph transformers bundled with the validator."""

from __future__ import annotations

import importlib
import pkgutil
from threading import Lock

_DISCOVERY_LOCK = Lock()
_TRANSFORMERS_LOADED = False


def load_transformers() -> None:
    """Import every bundled transformer module exactly once.

    Importing triggers function decorators and ``GraphTransformer`` subclass
    hooks. The lock prevents concurrent validations from observing a partially
    populated registry during first use.
    """
    global _TRANSFORMERS_LOADED  # noqa: PLW0603
    if _TRANSFORMERS_LOADED:
        return
    with _DISCOVERY_LOCK:
        if _TRANSFORMERS_LOADED:
            return
        package = importlib.import_module("rocrate_validator.transformers")
        package_prefix = f"{package.__name__}."
        for module in pkgutil.walk_packages(package.__path__, package_prefix):
            importlib.import_module(module.name)
        _TRANSFORMERS_LOADED = True
