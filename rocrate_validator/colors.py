from typing import Union

from .models import Severity


def get_severity_color(severity: Union[str, Severity]) -> str:
    """
    Get the color for the severity

    :param severity: The severity
    :return: The color
    """
    if severity == Severity.ERROR or severity == "ERROR":
        return "red"
    elif severity == Severity.MUST or severity == "MUST":
        return "red"
    elif severity == Severity.MUST_NOT or severity == "MUST_NOT":
        return "purple"
    elif severity == Severity.SHOULD or severity == "SHOULD":
        return "yellow"
    elif severity == Severity.SHOULD_NOT or severity == "SHOULD_NOT":
        return "lightyellow"
    elif severity == Severity.MAY or severity == "MAY":
        return "orange"
    elif severity == Severity.INFO or severity == "INFO":
        return "lightblue"
    elif severity == Severity.WARNING or severity == "WARNING":
        return "yellow green"
    else:
        return "white"
