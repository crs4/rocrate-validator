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

import atexit
import sys
import threading
from io import StringIO
from logging import (CRITICAL, DEBUG, ERROR, INFO, WARNING, Logger,
                     StreamHandler, basicConfig as logging_basicConfig)
from typing import Optional

import colorlog
from rich.console import Console
from rich.padding import Padding
from rich.rule import Rule
from rich.text import Text

# set the module to the current module
__module__ = sys.modules[__name__]


def get_log_format(level: int):
    """Get the log format based on the log level"""
    log_format = '[%(log_color)s%(asctime)s%(reset)s] %(levelname)s in %(yellow)s%(module)s%(reset)s: '\
        '%(light_white)s%(message)s%(reset)s'
    if level == DEBUG:
        log_format = '%(log_color)s%(levelname)s%(reset)s:%(yellow)s%(name)s:%(module)s::%(funcName)s%(reset)s '\
            '@ %(light_green)sline: %(lineno)s%(reset)s - %(light_black)s%(message)s%(reset)s'
    return log_format


DEFAULT_SETTINGS = {
    'enabled': True,
    'level': WARNING,
    'format': get_log_format(WARNING)
}


# _lock is used to serialize access to shared data structures in this module.
# This needs to be an RLock because fileConfig() creates and configures
# Handlers, and so might arbitrary user threads. Since Handler code updates the
# shared dictionary _handlers, it needs to acquire the lock. But if configuring,
# the lock would already have been acquired - so we need an RLock.
# The same argument applies to Loggers and Manager.loggerDict.
#
_lock = threading.RLock()


def _acquireLock():
    """
    Acquire the module-level lock for serializing access to shared data.

    This should be released with _releaseLock().
    """
    if _lock:
        _lock.acquire()


def _releaseLock():
    """
    Release the module-level lock acquired by calling _acquireLock().
    """
    if _lock:
        _lock.release()


# reference to the list of create loggers
__loggers__ = {}

# user settings for the loggers
__settings__ = DEFAULT_SETTINGS.copy()

# store logger handlers (only one handler per logger)
__handlers__ = {}


# Create a StringIO stream to capture the logs
__log_stream__ = StringIO()


# Define the callback function that will be called on exit
def __print_logs_on_exit__():
    log_contents = __log_stream__.getvalue()
    if not log_contents:
        return
    # print the logs
    console = Console()
    console.print(Padding(Rule("[bold cyan]Log Report[/bold cyan]", style="bold cyan"), (2, 0, 1, 0)))
    console.print(Padding(Text(log_contents), (0, 1)))
    console.print(Padding(Rule("", style="bold cyan"), (0, 0, 2, 0)))
    # close the stream
    __log_stream__.close()


# Register the callback with atexit
atexit.register(__print_logs_on_exit__)


def __setup_logger__(logger: Logger):

    # prevent the logger from propagating the log messages to the root logger
    logger.propagate = False

    # get the settings for the logger
    settings = __settings__.get(logger.name, __settings__)

    # parse the log level
    level = settings.get('level', __settings__['level'])
    if not isinstance(level, int):
        level = getattr(__module__, settings['level'].upper(), None)

    # set the log level
    logger.setLevel(level)

    # configure the logger handler
    ch = __handlers__.get(logger.name, None)
    if not ch:
        ch = StreamHandler(__log_stream__)
        ch.setLevel(level)
        ch.setFormatter(colorlog.ColoredFormatter(get_log_format(level)))
        logger.addHandler(ch)

    # enable/disable the logger
    if settings.get('enabled', __settings__['enabled']):
        logger.disabled = False
    else:
        logger.disabled = True


def __create_logger__(name: str) -> Logger:
    logger: Logger = None
    if not isinstance(name, str):
        raise TypeError('A logger name must be a string')
    _acquireLock()
    try:
        if name not in __loggers__:
            logger = colorlog.getLogger(name)
            __setup_logger__(logger)
            __loggers__[name] = logger
    finally:
        _releaseLock()
    return logger


def basicConfig(level: int, modules_config: Optional[dict] = None):
    """Set the log level and format for the logger"""
    _acquireLock()

    # set the default log level to ERROR for loggers of other modules
    logging_basicConfig(level=ERROR)

    # set the default log level and format
    try:
        if not isinstance(level, int):
            level = getattr(__module__, level.upper(), None)

        # set the default log level and format
        __settings__['level'] = level
        __settings__['format'] = get_log_format(level)

        # set the log level for the modules
        if modules_config:
            __settings__.update(modules_config)

        # initialize the logging module
        colorlog.basicConfig(
            level=__settings__['level'],
            format=__settings__['format'],
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            handlers=[StreamHandler(__log_stream__)]
        )

        # reconfigure existing loggers
        for logger in __loggers__.values():
            __setup_logger__(logger)

    finally:
        _releaseLock()


def getLogger(name: str) -> Logger:
    return LoggerProxy(name)


class LoggerProxy:

    """"Define a proxy class for the logger to allow lazy initialization of the logger instance"""

    def __init__(self, name: str):
        self.name = name
        self._instance = None

    def _initialize(self):
        _acquireLock()
        try:
            if self._instance is None:
                self._instance = __create_logger__(self.name)
        finally:
            _releaseLock()

    def __getattr__(self, name):
        self._initialize()
        return getattr(self._instance, name)


__export__ = [get_log_format, DEFAULT_SETTINGS, Logger,
              CRITICAL, DEBUG, ERROR, INFO, WARNING, StreamHandler, Optional]


# Example of usage
# if __name__ == '__main__':
# log_config = {
#     'module1': {'enabled': True, 'level': 'DEBUG'},
#     'module2': {'enabled': False, 'level': 'INFO'},
#     'module3': {'enabled': True, 'level': 'ERROR'},
# }
#     mgt = LoggerManager(log_config)
#     logger1 = mgt.getLogger('module1')
#     logger2 = mgt.getLogger('module2')
#     logger3 = mgt.getLogger('module3')
#     logger4 = mgt.getLogger('module4')

#     logger1.debug('This is a debug message')
#     logger1.info('This is an info message')
#     logger1.error('This is an error message')

#     logger2.debug('This is a debug message')
#     logger2.info('This is an info message')
#     logger2.error('This is an error message')

#     logger3.debug('This is a debug message')
#     logger3.info('This is an info message')
#     logger3.error('This is an error message')
#     logger3.critical('This is a critical message')

#     logger4.debug('This is a debug message')
#     logger4.info('This is an info message')
#     logger4.error('This is an error message')
#     logger4.critical('This is a critical message')
