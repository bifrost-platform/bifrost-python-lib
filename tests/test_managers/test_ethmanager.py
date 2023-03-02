import json
import os
import unittest
from time import sleep

from chainpy.eth.managers.consts import DEFAULT_BLOCK_PERIOD_SECS, DEFAULT_RPC_TX_BLOCK_DELAY, \
    DEFAULT_BLOCK_AGING_BLOCKS
from chainpy.eth.managers.ethchainmanager import EthChainManager
from tests.rpcendpointmock.procutil import kill_by_file_name
from tests.rpcendpointmock.rpcserver import MOCK_CHAIN_ID, ENDPOINT_URL


class TestEthManager(unittest.TestCase):
    def setUp(self) -> None:
        # launch mocking server
        self.server_launch_file_name = "../rpcendpointmock/rpcserver.py"
        self.launch_mock_server()

        self.test_chain_name = "TestChain"
        with open("../configs-event-test/entity.test.json", "r") as f:
            multichain_config = json.load(f)
            chain_config = multichain_config[self.test_chain_name]

        self.cli = EthChainManager.from_config_dict(chain_config)
        self.dummy_private_key = "0x01"
        self.expected_address = "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"

    def launch_mock_server(self):
        if kill_by_file_name(self.server_launch_file_name):
            print("[UnitTest] The server already exists -> killed it and relaunch the server")
        os.system("python {} &".format(self.server_launch_file_name))
        sleep(3)
        print("The server launched")

    def tearDown(self) -> None:
        result = kill_by_file_name(self.server_launch_file_name)
        print("server down") if result else print("No server")

    def test_cli_init(self):
        # EthRpcHandler's properties
        self.assertEqual(self.cli.chain_id, int(MOCK_CHAIN_ID, 16))
        self.assertEqual(self.cli.url, ENDPOINT_URL)
        self.assertEqual(self.cli.chain_name, self.test_chain_name)
        self.assertEqual(self.cli.resend_delay_sec, 3)

        expected_tx_commit_time = DEFAULT_BLOCK_PERIOD_SECS * (DEFAULT_RPC_TX_BLOCK_DELAY + DEFAULT_BLOCK_AGING_BLOCKS)
        self.assertEqual(self.cli.tx_commit_time_sec, expected_tx_commit_time)

        # EthChainManager's properties
        # Allow EthChainManager is initiated without account
        self.assertIsNone(self.cli.account)

        # Account can be set after EthChainManager initialization
        self.cli.set_account(self.dummy_private_key)
        self.assertEqual(self.cli.account.address, self.expected_address)

        # Nonce increments by one per use
        self.assertEqual(self.cli.issue_nonce, 10)
        self.assertEqual(self.cli.issue_nonce, 11)

        # Set to default config if config does not have fee information
        self.assertEqual(self.cli.fee_config.type, 0)
        self.assertEqual(self.cli.fee_config.type, self.cli.tx_type)
        self.assertEqual(self.cli.fee_config.gas_price, 2 ** 255 - 1)
        self.assertIsNone(self.cli.fee_config.max_gas_price)
        self.assertIsNone(self.cli.fee_config.max_priority_price)

    def test_send_transaction(self):
        # TODO test for below
        #  call_transaction,
        #  build_transaction,
        #  fetch_network_fee_parameters,
        #  set_gas_limit_and_fee,
        #  send_transaction
        #  transfer_native_coin
        #  native_balance (aka. get_balance)
        pass
