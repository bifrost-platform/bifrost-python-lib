import logging.handlers

from bridgeconst.consts import Chain
from chainpy.eth.ethtype.hexbytes import EthAddress


class LoggerSetting:
    LEVEL = logging.DEBUG
    FILENAME = None
    MAX_BYTES = 10 * 1024 * 1024
    BACKUP_COUNT = 10
    FORMAT = "%(asctime)s [%(name)-10s] %(message)s"


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


def Logger(
        name: str, level=LoggerSetting.LEVEL,
        max_bytes=LoggerSetting.MAX_BYTES, _format=LoggerSetting.FORMAT, file_path=LoggerSetting.FILENAME):
    # generate logger with "name"
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # define formatter and handler
    formatter = logging.Formatter(_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if file_path is not None:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=max_bytes,
            backupCount=LoggerSetting.BACKUP_COUNT
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
