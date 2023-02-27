import unittest

import uvicorn
from bridgeconst.consts import Chain
from rpcendpointmock.rpcserver import METHOD_503_ERROR, MOCK_CHAIN_ID, app, ENDPOINT_PORT
from chainpy.eth.managers.rpchandler import EthRpcClient


mockup_rpc_server = app


class TestContractHandler(unittest.TestCase):
    def setUp(self) -> None:
        result = uvicorn.run(mockup_rpc_server, port=ENDPOINT_PORT)
        print(type(result))
        print(result)

        self.cli = EthRpcClient.from_config_files(
            "./configs-event-test/entity.test.json",
            chain=Chain.BFC_TEST
        )

    def tearDown(self) -> None:
        # uvicorn.
        pass

    def test_simple_request(self):
        resp = self.cli.send_request("eth_chainId", [])
        print(type(resp))
        print(resp)

    def test_init(self):
        self.assertEqual(self.cli.chain_id, )
        print(self.cli.chain_id, MOCK_CHAIN_ID)

    def test_response_503(self):
        result = self.cli.send_request(METHOD_503_ERROR, [])
        print(result)
