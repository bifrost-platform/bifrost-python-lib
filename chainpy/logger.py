import logging.handlers
import os
from datetime import datetime
from pathlib import Path

from chainpy.eth.ethtype.hexbytes import EthAddress
from chainpy.eth.managers.consts import *


class LoggerConfig:
    def __init__(
        self,
        level: int = logging.DEBUG,
        log_format: str = "%(message)s",
        log_file_name: str = None,
        backup_count: int = 0,
        when: int = "H",
        interval: int = 1,
    ):
        self.level = level
        self.log_format = log_format
        self.log_file_name = log_file_name
        self.backup_count = backup_count
        self.when = when
        self.interval = interval

    def reset(
        self,
        level: int = logging.DEBUG,
        log_format: str = "%(message)s",
        log_file_name: str = None,
        backup_count: int = 0,
        when: int = "H",
        interval: int = 1,
    ):
        self.level = level
        self.log_format = log_format
        self.log_file_name = log_file_name
        self.backup_count = backup_count
        self.when = when
        self.interval = interval


logger_config_global = LoggerConfig()
BASE_LOG_DIR = "./logs/"


class Logger:
    NAME = "Logger"
    NAME_SIZE = 10
    TIME_FORMAT = "%y-%m-%d %H:%M:%S"

    def __init__(self):
        """ generate __logger with "name" """
        self.__logger = logging.getLogger(self.__class__.NAME)
        self.__logger.setLevel(logger_config_global.level)

    def init(
        self,
        level: str = logger_config_global.level,
        log_format: str = logger_config_global.log_format,
        log_file_name: str = logger_config_global.log_file_name,
        backup_count: int = logger_config_global.backup_count,
        when: str = "H",
        interval: int = 1
    ):
        self.__logger.setLevel(level)
        # define formatter and handler
        formatter = logging.Formatter(log_format)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.__logger.addHandler(stream_handler)

        if log_file_name is not None:
            if not Path(BASE_LOG_DIR).exists():
                os.mkdir(BASE_LOG_DIR)

            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=BASE_LOG_DIR + log_file_name,
                when=when,
                interval=interval,
                backupCount=backup_count
            )

            file_handler.setFormatter(formatter)
            self.__logger.addHandler(file_handler)
            self.info("Restart", "-" * 84)

    @staticmethod
    def _build_msg(name: str, msg: str):
        time_str = datetime.today().strftime(Logger.TIME_FORMAT)
        return "{} [{:-^10}] {}".format(time_str, name, msg)

    def debug(self, log_id: str, msg: str):
        formatted_msg = Logger._build_msg(log_id, msg)
        self.__logger.debug(formatted_msg)

    def info(self, log_id: str, msg: str):
        formatted_msg = Logger._build_msg(log_id, msg)
        self.__logger.info(formatted_msg)

    def warning(self, log_id: str, msg: str):
        formatted_msg = Logger._build_msg(log_id, msg)
        self.__logger.warning(formatted_msg)

    def error(self, log_id: str, msg: str):
        formatted_msg = Logger._build_msg(log_id, msg)
        self.__logger.error(formatted_msg)

    def exception(self, log_id: str, msg: str):
        formatted_msg = Logger._build_msg(log_id, msg)
        self.__logger.exception(formatted_msg)

    def critical(self, log_id: str, msg: str):
        formatted_msg = Logger._build_msg(log_id, msg)
        self.__logger.critical(formatted_msg)

    def fatal(self, log_id: str, msg: str):
        formatted_msg = Logger._build_msg(log_id, msg)
        self.__logger.fatal(formatted_msg)

    def log(self, level: int, msg: str):
        self.__logger.log(level, msg)

    def formatted_log(
        self,
        log_id: str,
        address: EthAddress = None,
        related_chain_name: str = DEFAULT_CHAIN_NAME,
        msg: str = None
    ):
        if log_id is None:
            return
        msg = "{}:{}:{}".format(
            address.hex()[:10] if address is not None else "NoAddress",
            related_chain_name,
            msg
        )
        self.info(log_id, msg)


global_logger = Logger()
