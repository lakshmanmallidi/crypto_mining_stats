import logging
import sys
from logging import FileHandler
from pythonjsonlogger import jsonlogger

json_formatter = jsonlogger.JsonFormatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(message)s")
formatter = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(message)s")
LOG_FILE = "file.log"


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    return console_handler


def get_file_handler(json):
    file_handler = FileHandler(LOG_FILE)
    if json:
        file_handler.setFormatter(json_formatter)
    else:
        file_handler.setFormatter(formatter)
    return file_handler


def get_logger(logger_name, log_level="info", json=False):
    logger = logging.getLogger(logger_name)

    if(log_level == "info"):
        logger.setLevel(logging.INFO)
    elif(log_level == "warning"):
        logger.setLevel(logging.WARNING)
    elif(log_level == "error"):
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.DEBUG)
    # logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler(json))
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    return logger
