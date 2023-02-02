class EstimateGasError(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class EthAlreadyImported(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class RpcEVMError(Exception):
    def __init__(self, msg: str):
        parsed_msg = msg.replace("VM Exception while processing transaction: ", "")
        parsed_msg = parsed_msg.replace("execution reverted: ", "")

        super().__init__("[{}] {}".format(self.__class__.__name__, parsed_msg))


class ReplaceTransactionUnderpriced(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class NonceTooLow(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class EthFeeCapError(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


def raise_integrated_exception(e):
    if isinstance(e, dict):
        error_msg = e["message"]
    else:
        error_msg = str(e)
    if error_msg.startswith("VM Exception while processing transaction: "):
        raise RpcEVMError(error_msg)
    elif error_msg.startswith("execution reverted: "):
        # TODO remove
        raise RpcEVMError(error_msg)
    elif error_msg.startswith("execution reverted"):
        raise RpcEVMError(error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(AlreadyImported("):
        raise EthAlreadyImported(error_msg)
    elif error_msg.startswith("nonce too low"):
        raise NonceTooLow(error_msg)
    elif error_msg.startswith("replacement transaction underpriced") or error_msg.startswith("transaction underpriced"):
        raise ReplaceTransactionUnderpriced(error_msg)
    elif error_msg.startswith("tx fee("):
        raise EthFeeCapError(error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(TooLowPriority { old"):
        raise NonceTooLow(error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(InvalidTransaction"):
        raise NonceTooLow(error_msg)
    else:
        raise Exception("Not handled error: {}".format(error_msg))
