import logging.handlers

from bridgeconst.consts import Chain
from chainpy.eth.ethtype.hexbytes import EthAddress


class LoggerSetting:
    def __init__(
            self,
            level: int = logging.DEBUG,
            file_path: str = None,
            max_bytes: int = 10 * 1024 * 1024,
            backup_count: int = 10,
            log_format: str = "%(asctime)s [%(name)-12s] %(message)s"
    ):
        self.level = level
        self.file_path = file_path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.log_format = log_format

    def reset(
            self,
            level: int = logging,
            file_path: str = None,
            max_bytes: int = 10 * 1024 * 1024,
            backup_count: int = 10,
            log_format: str = "%(asctime)s [%(name)-10s] %(message)s"
    ):
        self.level = level
        self.file_path = file_path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.log_format = log_format


logger_setting_global = LoggerSetting()


class Logger:
    def __init__(self, name: str, level: int = logger_setting_global.level):
        """ generate logger with "name" """
        self.name = name
        self.level = level
        self.logger = None
        self.reset(name, level)

    def reset(self, name: str = None, level: int = None):
        _name = self.name if name is None else name
        self.logger = logging.getLogger(_name)

        if len(self.logger.handlers) > 0:
            return

        _level = self.level if level is None else level
        self.logger.setLevel(_level)

        # define formatter and handler
        formatter = logging.Formatter(logger_setting_global.log_format)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

        if logger_setting_global.file_path is not None:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=logger_setting_global.file_path,
                maxBytes=logger_setting_global.max_bytes,
                backupCount=logger_setting_global.backup_count
            )

            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def info(self, msg: str):
        self.logger.info(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def formatted_log(
            self,
            relayer_addr: EthAddress = EthAddress.default(),
            log_id: str = None,
            related_chain: Chain = None,
            log_data: str = None):
        if log_id is None:
            return
        msg = "{}:{}:{}:{}".format(
            relayer_addr.hex()[:10],
            log_id,
            related_chain,
            log_data
        )
        self.logger.info(msg)
