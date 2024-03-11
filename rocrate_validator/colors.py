from .models import Severity


def get_severity_color(severity: Severity) -> str:
    """
    Get the color for the severity

    :param severity: The severity
    :return: The color
    """
    if severity == Severity.ERROR:
        return "red"
    elif severity == Severity.MUST:
        return "red"
    elif severity == Severity.MUST_NOT:
        return "purple"
    elif severity == Severity.SHOULD:
        return "yellow"
    elif severity == Severity.SHOULD_NOT:
        return "lightyellow"
    elif severity == Severity.MAY:
        return "orange"
    elif severity == Severity.INFO:
        return "lightblue"
    elif severity == Severity.WARNING:
        return "yellow green"
    else:
        return "white"
