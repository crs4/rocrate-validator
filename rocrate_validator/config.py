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

import logging
import colorlog


def configure_logging(level: int = logging.WARNING):
    """
    Configure the logging for the package

    :param level: The logging level
    """
    log_format = '[%(log_color)s%(asctime)s%(reset)s] %(levelname)s in %(yellow)s%(module)s%(reset)s: '\
        '%(light_white)s%(message)s%(reset)s'
    if level == logging.DEBUG:
        log_format = '%(log_color)s%(levelname)s%(reset)s:%(yellow)s%(name)s:%(module)s::%(funcName)s%(reset)s '\
            '@ %(light_green)sline: %(lineno)s%(reset)s - %(light_black)s%(message)s%(reset)s'

    colorlog.basicConfig(
        level=level,
        format=log_format,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
    )
