import os
import unittest
from tests.rpcendpointmock.procutil import kill_by_file_name

from bridgeconst.consts import Chain
from chainpy.eth.managers.rpchandler import EthRpcClient

from rpcendpointmock.rpcserver import METHOD_503_ERROR, MOCK_CHAIN_ID, ENDPOINT_PORT


class TestContractHandler(unittest.TestCase):
    def setUp(self) -> None:
        # launch mocking server
        self.server_launch_file_name = "rpcendpointmock/rpcserver.py"
        os.system("python {} &".format(self.server_launch_file_name))

        self.cli = EthRpcClient.from_config_files(
            "./configs-event-test/entity.test.json",
            chain=Chain.BFC_TEST
        )

    def tearDown(self) -> None:
        result = kill_by_file_name(self.server_launch_file_name)
        print("server down") if result else print("No server")

    def test_base(self):
        print("hello")
