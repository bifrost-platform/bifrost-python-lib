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
            log_format: str = "%(asctime)s [%(name)-10s] %(message)s"
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


def formatted_log(
        logger_obj,
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
    logger_obj.info(msg)


def Logger(name: str, level=logger_setting_global.level):
    """ generate logger with "name" """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # define formatter and handler
    formatter = logging.Formatter(logger_setting_global.log_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if logger_setting_global.file_path is not None:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=logger_setting_global.file_path,
            maxBytes=logger_setting_global.max_bytes,
            backupCount=logger_setting_global.backup_count
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
