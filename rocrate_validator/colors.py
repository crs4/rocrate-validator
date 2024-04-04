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
        return "orange"
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
        return "yellow"
    elif level == LevelCollection.SHOULD_NOT:
        return "lightyellow"
    elif level in (LevelCollection.MAY, LevelCollection.OPTIONAL):
        return "orange"
    else:
        return "white"
