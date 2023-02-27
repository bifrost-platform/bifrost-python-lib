import unittest

from bridgeconst.consts import Chain

from chainpy.eth.managers.rpchandler import EthRpcClient


class TestContractHandler(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = EthRpcClient.from_config_files(
            "./configs-event-test/entity.test.json",
            chain=Chain.BFC_TEST
        )

    def test_simple_request(self):
        resp = self.cli.send_request("eth_chainId", [])
        print(type(resp))
        print(resp)
