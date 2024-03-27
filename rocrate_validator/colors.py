from typing import Union

from .models import RequirementLevel, Severity


def get_severity_color(severity: Union[str, Severity]) -> str:
    """
    Get the color for the severity

    :param severity: The severity
    :return: The color
    """
    if severity == Severity.REQUIRED or severity == "REQUIRED":
        return "red"
    elif severity == Severity.RECOMMENDED or severity == "RECOMMENDED":
        return "orange"
    elif severity == Severity.OPTIONAL or severity == "OPTIONAL":
        return "yellow"
    else:
        return "white"


def get_req_level_color(level: RequirementLevel) -> str:
    """
    Get the color for a RequirementLevel

    :return: The color
    """
    if level in (RequirementLevel.MUST, RequirementLevel.SHALL, RequirementLevel.REQUIRED):
        return "red"
    elif level in (RequirementLevel.MUST_NOT, RequirementLevel.SHALL_NOT):
        return "purple"
    elif level in (RequirementLevel.SHOULD, RequirementLevel.RECOMMENDED):
        return "yellow"
    elif level == RequirementLevel.SHOULD_NOT:
        return "lightyellow"
    elif level in (RequirementLevel.MAY, RequirementLevel.OPTIONAL):
        return "orange"
    else:
        return "white"
