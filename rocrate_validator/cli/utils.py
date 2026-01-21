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

import os

from rocrate_validator.utils import log as logging

# set up logging
logger = logging.getLogger(__name__)


def running_in_jupyter():
    # Environment variable set by Jupyter to indicate
    # the process ID (PID) of the Jupyter server
    # that launched the current kernel.
    # It is mainly used internally to track the parent process
    # and manage kernel lifecycle.
    return 'JPY_PARENT_PID' in os.environ
