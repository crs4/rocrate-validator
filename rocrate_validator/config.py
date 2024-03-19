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
