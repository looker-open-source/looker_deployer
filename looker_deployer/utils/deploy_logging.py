import logging
from datetime import datetime
from pythonjsonlogger import jsonlogger


class MetricLogger(logging.Logger):
    COUNT = "COUNT"
    BYTES = "BYTES"

    _valid_units = {COUNT, BYTES}

    def measure(self, measure, value, unit, level=logging.INFO):
        """
        Expands standard logging to enforce consistent attributes for measurements/instrumentation
        :param measure: the name of the measurement (what will be aggregated and reported on)
        :param value: the value of the measurement (will be force casted to float)
        :param unit: a valid unit of measure defined in the class (e.g., .COUNT, .BYTES)
        :param level: the logging level to use for output (default logging.INFO)
        :return: None
        """
        lvl_name = logging.getLevelName(level).lower()
        assert (
            unit in MetricLogger._valid_units
        ), f"Must use one of {', '.join(MetricLogger._valid_units)}"
        getattr(self, lvl_name)(
            "measure", extra={"measure": measure, "value": float(value), "unit": unit}
        )


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    TS_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.utcfromtimestamp(record.created).strftime(
            CustomJsonFormatter.TS_FORMAT
        )


def get_logger(name, handler=None):
    logger = MetricLogger(name)
    if handler is None:
        handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(
        "%(levelname) %(module) %(funcName) %(message)"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
