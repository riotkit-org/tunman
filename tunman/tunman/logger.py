
import sys
import logging
from copy import copy


this = sys.modules[__name__]
MAPPING = {
    'DEBUG': 37,
    'INFO': 36,
    'WARNING': 33,
    'ERROR': 31,
    'CRITICAL': 41
}

PARAM_MAPPING = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

PREFIX = '\033['
SUFFIX = '\033[0m'


class ColoredFormatter(logging.Formatter):
    def __init__(self, pattern):
        logging.Formatter.__init__(self, pattern)

    def format(self, record):
        colored_record = copy(record)
        level_name = colored_record.levelname

        seq = MAPPING.get(level_name, 37)
        colored_level_name = '{0}{1}m{2}{3}' \
            .format(PREFIX, seq, level_name, SUFFIX)
        colored_record.levelname = colored_level_name

        return logging.Formatter.format(self, colored_record)


def setup_dummy_logger():
    logger = logging.getLogger('tunman')
    for handler in logger.handlers:
        logger.removeHandler(handler)
    this.logger = logger


def setup_logger(path: str, level: str):
    """ Creates a logger instance with proper handlers configured """

    logger = logging.getLogger('tunman')
    logger.setLevel(logging.INFO)
    formatter = ColoredFormatter("[%(asctime)s][%(name)s][%(levelname)s]: %(message)s")

    logging_handler = logging.StreamHandler(sys.stdout)
    logging_handler.setFormatter(formatter)

    log_file_handler = logging.FileHandler(path, 'a+')
    log_file_handler.setFormatter(formatter)

    level = PARAM_MAPPING[level] if level in PARAM_MAPPING else PARAM_MAPPING['info']
    logger.setLevel(level)
    logging_handler.setLevel(level)
    log_file_handler.setLevel(level)

    for handler in logger.handlers:
        logger.removeHandler(handler)

    logger.addHandler(logging_handler)

    this.logger = logger


class Logger:
    @staticmethod
    def debug(msg: str):
        this.logger.debug(msg)

    @staticmethod
    def info(msg: str):
        this.logger.info(msg)

    @staticmethod
    def warning(msg: str):
        this.logger.warning(msg)

    @staticmethod
    def error(msg: str):
        this.logger.error(msg)
