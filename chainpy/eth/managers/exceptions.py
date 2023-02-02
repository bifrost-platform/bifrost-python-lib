from typing import Union, Optional

from bridgeconst.consts import Chain


class CustomException(Exception):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__("[{}] {}".format(related_chain.name, msg))


class RpCMaxRetry(CustomException):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__(related_chain, msg)


class RpcOutOfStatusCode(CustomException):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__(related_chain, msg)


class RpcErrorResult(CustomException):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__(related_chain, msg)


class RpcNoneResult(CustomException):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__(related_chain, msg)


class EstimateGasError(Exception):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__("[{}] {}".format(related_chain.name, msg))


class EthAlreadyImported(Exception):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__("[{}] {}".format(related_chain.name, msg))


class RpcEVMError(Exception):
    def __init__(self, related_chain: Chain, msg: str):
        parsed_msg = msg.replace("VM Exception while processing transaction: ", "")
        parsed_msg = parsed_msg.replace("execution reverted: ", "")
        super().__init__("[{}] {}".format(related_chain.name, parsed_msg))


class ReplaceTransactionUnderpriced(Exception):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__("[{}] {}".format(related_chain.name, msg))


class NonceTooLow(Exception):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__("[{}] {}".format(related_chain.name, msg))


class EthFeeCapError(Exception):
    def __init__(self, related_chain: Chain, msg: str):
        super().__init__("[{}] {}".format(related_chain.name, msg))


def raise_integrated_exception(
        chain: Chain,
        e: Exception = None,
        error_msg: Optional[Union[str, dict]] = None,
        is_none_result: bool = False
):
    if is_none_result:
        raise RpcNoneResult(chain, "None rpc-result")
    elif isinstance(e, dict):
        error_msg = e["message"]
    else:
        error_msg = str(e)

    if error_msg.startswith("VM Exception while processing transaction: "):
        raise RpcEVMError(chain, error_msg)
    elif error_msg.startswith("execution reverted: "):
        raise RpcEVMError(chain, error_msg)
    elif error_msg.startswith("execution reverted"):
        raise RpcEVMError(chain, error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(AlreadyImported("):
        raise EthAlreadyImported(chain, error_msg)
    elif error_msg.startswith("nonce too low"):
        raise NonceTooLow(chain, error_msg)
    elif error_msg.startswith("replacement transaction underpriced") or error_msg.startswith("transaction underpriced"):
        raise ReplaceTransactionUnderpriced(chain, error_msg)
    elif error_msg.startswith("tx fee("):
        raise EthFeeCapError(chain, error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(TooLowPriority { old"):
        raise NonceTooLow(chain, error_msg)
    elif error_msg.startswith("submit transaction to pool failed: Pool(InvalidTransaction"):
        raise NonceTooLow(chain, error_msg)
    else:
        raise Exception("Not handled error on {}: {}".format(chain.name, error_msg))
