import json

import uvicorn
from fastapi import FastAPI, Request, Response
from jsonrpcserver import Result, Success, dispatch, method
from starlette import status

ENDPOINT_BASE_URL = "http://localhost"
ENDPOINT_PORT = 5001
ENDPOINT_URL = ENDPOINT_BASE_URL + ":" + str(ENDPOINT_PORT)

MOCK_CHAIN_ID = "0xbfc0"
METHOD_503_ERROR = "server_error_503"
EMPTY_RESPONSE = ""

app = FastAPI()


@method
def eth_chainId() -> Result:
    return Success(MOCK_CHAIN_ID)


@method
def server_error_503() -> Result:
    print(3)
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
    if rpc_method == "server_error_503":
        resp.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return resp


if __name__ == "__main__":
    uvicorn.run(app, port=ENDPOINT_PORT)
