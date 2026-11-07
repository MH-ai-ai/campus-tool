import logging
import re
from logging import NullHandler
from logging.handlers import RotatingFileHandler

from .paths import LOG_PATH


LOGGER_NAME = "CampusGuard"


class SensitiveDataFilter(logging.Filter):
    """过滤并脱敏日志中可能包含的明文密码、API Token 及敏感认证参数。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self.sanitize(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self.sanitize(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True

    @classmethod
    def sanitize(cls, text: str) -> str:
        # 1. 过滤 URL 参数与键值对中的密码字段
        text = re.sub(
            r'((?:user_password|password|pwd|secret|token)=)([^&\s\'"]+)',
            r'\1******',
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r'((?:user_password|password|pwd|secret|token)"?\s*[:=]\s*["\'])([^"\']+)(["\'])',
            r'\1******\3',
            text,
            flags=re.IGNORECASE,
        )
        # 2. 过滤 Telegram Bot Token 中的 secret key: bot123456:ABC... -> bot123456:******
        text = re.sub(
            r'(bot\d+:)[A-Za-z0-9_-]+',
            r'\1******',
            text,
        )
        return text


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(NullHandler())
    return logger


def setup_logging() -> logging.Logger:
    logger = get_logger()
    real_handlers = [handler for handler in logger.handlers if not isinstance(handler, NullHandler)]
    if real_handlers:
        return logger
    logger.handlers = [
        handler for handler in logger.handlers if not isinstance(handler, NullHandler)
    ]

    logger.setLevel(logging.INFO)
    sensitive_filter = SensitiveDataFilter()
    logger.addFilter(sensitive_filter)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sensitive_filter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(sensitive_filter)
    logger.addHandler(stream_handler)

    logger.propagate = False
    return logger

