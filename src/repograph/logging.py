"""JSON logs go to stderr; stdout belongs exclusively to MCP."""

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {"level": record.levelname, "logger": record.name, "message": record.getMessage()}
        )


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("repograph")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
