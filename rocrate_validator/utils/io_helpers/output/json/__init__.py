
from typing import Any, Optional

from rocrate_validator.utils import log as logging
from rocrate_validator.utils.io_helpers.output import BaseOutputFormatter
from rocrate_validator.utils.io_helpers.output.json.formatters import (
    ValidationResultJSONOutputFormatter, ValidationResultsJSONOutputFormatter,
    ValidationStatisticsJSONOutputFormatter)
from rocrate_validator.models import ValidationResult, ValidationStatistics

# set up logging
logger = logging.getLogger(__name__)


class JSONOutputFormatter(BaseOutputFormatter):

    def __init__(self, data: Optional[Any] = None):
        super().__init__(data)
        self.add_type_formatter(ValidationResult, ValidationResultJSONOutputFormatter)
        self.add_type_formatter(dict, ValidationResultsJSONOutputFormatter)
        self.add_type_formatter(ValidationStatistics, ValidationStatisticsJSONOutputFormatter)
