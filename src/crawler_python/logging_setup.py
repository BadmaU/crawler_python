import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_configured = False


class LevelFilter(logging.Filter):
    """Фильтр записей по минимальному уровню (для предотвращения дублирования)."""

    def __init__(self, min_level: int) -> None:
        super().__init__()
        self._min_level = min_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self._min_level


def setup_logging(
    level: str | int = logging.INFO,
    log_file: str | None = "crawler.log",
    console: bool = True,
    rotation_backups: int = 5,
    max_bytes: int = 5_000_000,
    name: str = "crawler_python",
    force: bool = False,
) -> logging.Logger:
    """Настройка структурированного логирования в файл и консоль.

    - Запись в файл и консоль (в зависимости от флага).
    - Разные уровни (DEBUG, INFO, WARNING, ERROR).
    - Ротация логов через RotatingFileHandler.
    - Форматирование с временными метками.
    """
    global _configured

    logger = logging.getLogger(name)
    if logger.handlers and not force:
        return logger

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(LevelFilter(logging.DEBUG))
        logger.addHandler(console_handler)

    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=rotation_backups,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if force:
        _configured = True

    return logger
