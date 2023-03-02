import copy
import json

import uvicorn
from fastapi import FastAPI, Request, Response
from jsonrpcserver import Result, Success, dispatch, method

from tests.rpcendpointmock.data import *
from tests.rpcendpointmock.util import change_block_verbosity

ENDPOINT_BASE_URL = "http://127.0.0.1"
ENDPOINT_PORT = 5001
ENDPOINT_URL = ENDPOINT_BASE_URL + ":" + str(ENDPOINT_PORT)

EMPTY_RESPONSE = ""
METHOD_503_ERROR = "server_error_503"

MOCK_CHAIN_ID = "0xbfcbfc"
MOCK_LATEST_HEIGHT = hex(max(MOCK_BLOCKS.keys()))
GET_RECEIPT_WAIT_ITER = 3

app = FastAPI()


@method
def eth_chainId() -> Result:
    return Success(MOCK_CHAIN_ID)


@method
def eth_blockNumber() -> Result:
    return Success(MOCK_LATEST_HEIGHT)


@method
def eth_getBlockByNumber(height: str, verbose: bool) -> Result:
    target_height = max(MOCK_BLOCKS.keys()) if height == "latest" else int(height, 16)

    block = copy.deepcopy(MOCK_BLOCKS.get(target_height))
    if verbose or block is None:
        return Success(block)
    else:
        verbose_false_block = change_block_verbosity(block)
        return Success(verbose_false_block)


@method
def eth_getBlockByHash(hash: str, verbose: bool) -> Result:
    for height, block in MOCK_BLOCKS.items():
        if block["hash"] == hash:
            if not verbose:
                verbose_false_block = change_block_verbosity(block)
                return Success(verbose_false_block)
            else:
                return Success(block)
    return Success(None)


@method
def eth_getTransactionByHash(hash: str) -> Result:
    if hash == TEST_TRANSACTION_HASH:
        return Success(MOCK_BLOCKS[TEST_HEIGHT]["transactions"][0])
    else:
        return Success(None)


@method
def eth_getTransactionByBlockNumberAndIndex(number: str, index: str) -> Result:
    if number == hex(TEST_HEIGHT) and index == hex(TEST_TRANSACTION_INDEX):
        return Success(MOCK_BLOCKS[TEST_HEIGHT]["transactions"][TEST_TRANSACTION_INDEX])
    else:
        return Success(None)


@method
def eth_getTransactionByBlockHashAndIndex(hash: str, index: str):
    if hash == TEST_BLOCK_HASH and index == hex(0):
        return Success(MOCK_BLOCKS[3982085]["transactions"][0])
    else:
        return Success(None)


class Counter:
    def __init__(self, limit: int = GET_RECEIPT_WAIT_ITER):
        self._cnt = 0
        self.limit = limit

    def inc(self):
        self._cnt += 1

    def is_limit(self) -> bool:
        return self._cnt >= self.limit

    def get_value(self) -> int:
        return self._cnt


cnt = Counter(GET_RECEIPT_WAIT_ITER)


@method
def eth_getTransactionReceipt(hash: str) -> Result:
    if hash == TEST_TRANSACTION_HASH:
        return Success(TEST_RECEIPT)
    if hash == TEST_ADDITIONAL_TX_HASH:
        # return meaningful response after GET_RECEIPT_WAIT_ITER request
        cnt.inc()
        if cnt.is_limit():
            return Success(ADDITIONAL_RECEIPT)
        else:
            return Success(None)
    else:
        Success(None)


@method
def eth_getBalance(address: str, height: str) -> Result:
    return Success(1000000000000000000)


@method
def server_error_503() -> Result:
    return Success(EMPTY_RESPONSE)


@method
def server_error_502() -> Result:
    return Success(EMPTY_RESPONSE)


@method
def server_error_429() -> Result:
    return Success(EMPTY_RESPONSE)


@method
def server_error_404() -> Result:
    return Success(EMPTY_RESPONSE)


@app.post("/")
async def index(request: Request):
    req_body = await request.body()
    resp = Response(dispatch(req_body))
    rpc_method = json.loads(req_body.decode())["method"]
    if rpc_method.startswith("server_error"):
        resp.status_code = int(rpc_method.split("_")[-1])

    return resp


if __name__ == "__main__":
    uvicorn.run(app, port=ENDPOINT_PORT)
