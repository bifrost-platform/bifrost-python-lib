from typing import Union, Optional


class CustomException(Exception):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__("[{}] {}".format(related_chain_name, msg))


class RpCMaxRetry(CustomException):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__(related_chain_name, msg)


class RpcOutOfStatusCode(CustomException):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__(related_chain_name, msg)


class RpcErrorResult(CustomException):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__(related_chain_name, msg)


class RpcNoneResult(CustomException):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__(related_chain_name, msg)


class EstimateGasError(Exception):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__("[{}] {}".format(related_chain_name, msg))


class EthAlreadyImported(Exception):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__("[{}] {}".format(related_chain_name, msg))


class RpcEVMError(Exception):
    def __init__(self, related_chain_name: str, msg: str):
        parsed_msg = msg.replace("VM Exception while processing transaction: ", "")
        parsed_msg = parsed_msg.replace("execution reverted: ", "")
        super().__init__("[{}] {}".format(related_chain_name, parsed_msg))


class ReplaceTransactionUnderpriced(Exception):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__("[{}] {}".format(related_chain_name, msg))


class NonceTooLow(Exception):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__("[{}] {}".format(related_chain_name, msg))


class EthFeeCapError(Exception):
    def __init__(self, related_chain_name: str, msg: str):
        super().__init__("[{}] {}".format(related_chain_name, msg))


def raise_integrated_exception(
        chain_name: str,
        e: Exception = None,
        error_json: Optional[Union[str, dict]] = None,
        is_none_result: bool = False
):
    if is_none_result:
        raise RpcNoneResult(chain_name, "None rpc-result")
    elif isinstance(error_json, dict):
        error_msg = error_json["message"]
    else:
        error_msg = str(e)

    if error_msg.startswith("VM Exception while processing transaction: "):
        raise RpcEVMError(chain_name, error_msg)
    elif error_msg.startswith("execution reverted: "):
        raise RpcEVMError(chain_name, error_msg)
    elif error_msg.startswith("execution reverted"):
        raise RpcEVMError(chain_name, error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(AlreadyImported("):
        raise EthAlreadyImported(chain_name, error_msg)
    elif error_msg.startswith("nonce too low"):
        raise NonceTooLow(chain_name, error_msg)
    elif error_msg.startswith("replacement transaction underpriced") or error_msg.startswith("transaction underpriced"):
        raise ReplaceTransactionUnderpriced(chain_name, error_msg)
    elif error_msg.startswith("tx fee("):
        raise EthFeeCapError(chain_name, error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(TooLowPriority { old"):
        raise NonceTooLow(chain_name, error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(InvalidTransaction"):
        raise NonceTooLow(chain_name, error_msg)
    else:
        raise Exception("Not handled error on {}: {}".format(chain_name, error_msg))
