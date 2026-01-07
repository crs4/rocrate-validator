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

import toml

from rocrate_validator.utils import log as logging

# set up logging
logger = logging.getLogger(__name__)

# cache the configuration
_config = None


def get_config() -> dict:
    """
    Get the configuration for the package or a specific property

    :return: The configuration
    """
    global _config
    if _config is None:
        from .paths import get_config_path

        # Read the pyproject.toml file
        _config = toml.load(get_config_path())

    return _config
