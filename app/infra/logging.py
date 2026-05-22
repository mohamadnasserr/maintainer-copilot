import logging
from typing import Any

from app.infra.redaction import redact_for_log


class SafeLogFilter(logging.Filter):
    """
    Ensures every log record has request_id and trace_id,
    and redacts sensitive content before output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "none"

        if not hasattr(record, "trace_id"):
            record.trace_id = "none"

        record.msg = redact_for_log(record.getMessage())
        record.args = ()

        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SafeLogFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s trace_id=%(trace_id)s request_id=%(request_id)s %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)