import os
import unittest
from time import sleep

from tests.rpcendpointmock.procutil import kill_by_file_name

from bridgeconst.consts import Chain
from chainpy.eth.managers.rpchandler import EthRpcClient

from rpcendpointmock.rpcserver import METHOD_503_ERROR, MOCK_CHAIN_ID, ENDPOINT_PORT, ENDPOINT_URL


class TestContractHandler(unittest.TestCase):
    def setUp(self) -> None:
        # launch mocking server
        self.server_launch_file_name = "rpcendpointmock/rpcserver.py"
        self.launch_mock_server()

        self.cli = EthRpcClient.from_config_files(
            "./configs-event-test/entity.test.json",
            chain=Chain.ETH_GOERLI
        )
        self.cli.url = ENDPOINT_URL

    def launch_mock_server(self):
        if kill_by_file_name(self.server_launch_file_name):
            print("[UnitTest] The server already exists -> killed it and relaunch the server")
        os.system("python {} &".format(self.server_launch_file_name))
        sleep(3)
        print("The server launched")

    def tearDown(self) -> None:
        result = kill_by_file_name(self.server_launch_file_name)
        print("server down") if result else print("No server")

    def test_send_request_success(self):
        print("entered")
        result = self.cli.send_request("eth_chainId", [])
        print(result)
        self.assertTrue(isinstance(result, str))
        self.assertEqual(result, "0xbfc0")

        # self.assertRaises(Exception, self.cli.send_request, "eth_chainI", [])

    def test_send_request_503_exception(self):
        result = self.cli.send_request("server_error_503", [])
        print(result)
