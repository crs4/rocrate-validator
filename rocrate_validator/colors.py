from .checks import IssueSeverity


def get_severity_color(severity: IssueSeverity) -> str:
    """
    Get the color for the severity

    :param severity: The severity
    :return: The color
    """
    if severity == IssueSeverity.ERROR:
        return "red"
    elif severity == IssueSeverity.MUST:
        return "red"
    elif severity == IssueSeverity.MUST_NOT:
        return "purple"
    elif severity == IssueSeverity.SHOULD:
        return "yellow"
    elif severity == IssueSeverity.SHOULD_NOT:
        return "lightyellow"
    elif severity == IssueSeverity.MAY:
        return "orange"
    elif severity == IssueSeverity.INFO:
        return "lightblue"
    elif severity == IssueSeverity.WARNING:
        return "yellow green"
    else:
        return "white"
