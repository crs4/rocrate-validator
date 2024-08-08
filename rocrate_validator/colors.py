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

from typing import Union

from .models import LevelCollection, Severity


def get_severity_color(severity: Union[str, Severity]) -> str:
    """
    Get the color for the severity

    :param severity: The severity
    :return: The color
    """
    if severity == Severity.REQUIRED or severity == "REQUIRED":
        return "red"
    elif severity == Severity.RECOMMENDED or severity == "RECOMMENDED":
        return "orange1"
    elif severity == Severity.OPTIONAL or severity == "OPTIONAL":
        return "yellow"
    else:
        return "white"


def get_req_level_color(level: LevelCollection) -> str:
    """
    Get the color for a LevelCollection

    :return: The color
    """
    if level in (LevelCollection.MUST, LevelCollection.SHALL, LevelCollection.REQUIRED):
        return "red"
    elif level in (LevelCollection.MUST_NOT, LevelCollection.SHALL_NOT):
        return "purple"
    elif level in (LevelCollection.SHOULD, LevelCollection.RECOMMENDED):
        return "orange1"
    elif level == LevelCollection.SHOULD_NOT:
        return "lightyellow"
    elif level in (LevelCollection.MAY, LevelCollection.OPTIONAL):
        return "yellow"
    else:
        return "white"
