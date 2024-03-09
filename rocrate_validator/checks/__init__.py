from importlib import import_module
import inspect
import os
import re
import logging
from typing import List

# set up logging
logger = logging.getLogger(__name__)

# current directory
__CURRENT_DIR__ = os.path.dirname(os.path.realpath(__file__))


def get_checks(directory: str = __CURRENT_DIR__, instaces: bool = True) -> List[str]:
    """
    Load all the classes from the directory
    """
    logger.debug("Loading checks from %s", directory)
    # create an empty list to store the classes
    classes = {}
    # loop through the files in the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # check if the file is a python file
            logger.debug("Checking file %s", file)
            if file.endswith(".py") and not file.startswith("__init__"):
                # get the file path
                file_path = os.path.join(root, file)
                # FIXME: works only on the main "general" general directory
                m = '{}.{}'.format(
                    'rocrate_validator.checks', os.path.basename(file_path)[:-3])
                logger.debug("Module: %r" % m)
                # import the module
                mod = import_module(m)
                # loop through the objects in the module
                # and store the classes
                for _, obj in inspect.getmembers(mod):
                    logger.debug("Checking object %s", obj)
                    if inspect.isclass(obj) \
                            and inspect.getmodule(obj) == mod \
                            and obj.__name__.endswith('Check'):
                        classes[obj.__name__] = obj
                        logger.debug("Loaded class %s", obj.__name__)
                return [v() if instaces else v for v in classes.values()]

    # return the list of classes
    return classes
