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

import inspect
import os
import re
import sys
from importlib import import_module
from pathlib import Path
from typing import Optional

from rocrate_validator.utils import log as logging

# set up logging
logger = logging.getLogger(__name__)


def get_classes_from_file(file_path: Path,
                          filter_class: Optional[type] = None,
                          class_name_suffix: Optional[str] = None) -> dict[str, type]:
    """Get all classes in a Python file """
    # ensure the file path is a Path object
    assert file_path, "The file path is required"
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Check if the file is a Python file
    if not file_path.exists():
        raise ValueError("The file does not exist")

    # Check if the file is a Python file
    if file_path.suffix != ".py":
        raise ValueError("The file is not a Python file")

    # Get the module name from the file path
    module_name = file_path.stem
    logger.debug("Module: %r", module_name)

    # Add the directory containing the file to the system path
    sys.path.insert(0, os.path.dirname(file_path))

    # Import the module
    module = import_module(module_name)
    logger.debug("Module: %r", module)

    # Get all classes in the module that are subclasses of filter_class
    classes = {name: cls for name, cls in inspect.getmembers(module, inspect.isclass)
               if cls.__module__ == module_name
               and (not class_name_suffix or cls.__name__.endswith(class_name_suffix))
               and (not filter_class or (issubclass(cls, filter_class) and cls != filter_class))}

    return classes


def to_camel_case(snake_str: str) -> str:
    """
    Convert a snake case string to camel case

    :param snake_str: The snake case string
    :return: The camel case string
    """
    components = re.split('_|-', snake_str)
    return components[0].capitalize() + ''.join(x.title() for x in components[1:])


def get_requirement_name_from_file(file: Path, check_name: Optional[str] = None) -> str:
    """
    Get the requirement name from the file

    :param file: The file
    :return: The requirement name
    """
    assert file, "The file is required"
    if not isinstance(file, Path):
        file = Path(file)
    base_name = to_camel_case(file.stem)
    if check_name:
        return f"{base_name}.{check_name.replace('Check', '')}"
    return base_name


def get_requirement_class_by_name(requirement_name: str) -> type:
    """
    Dynamically load the module of the class and return the class"""

    # Split the requirement name into module and class
    module_name, class_name = requirement_name.rsplit(".", 1)
    logger.debug("Module: %r", module_name)
    logger.debug("Class: %r", class_name)

    # convert the module name to a path
    module_path = module_name.replace(".", "/")
    # add the path to the system path
    sys.path.insert(0, os.path.dirname(module_path))

    # Import the module
    module = import_module(module_name)

    # Get the class from the module
    return getattr(module, class_name)
