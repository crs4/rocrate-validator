import toml

from rocrate_validator.utils import log as logging

# set up logging
logger = logging.getLogger(__name__)

# cache the configuration
_config = None


def get_config() -> dict:
    """
    Get the configuration for the package or a specific property

    :return: The configuration
    """
    global _config
    if _config is None:
        from .paths import get_config_path

        # Read the pyproject.toml file
        _config = toml.load(get_config_path())

    return _config
