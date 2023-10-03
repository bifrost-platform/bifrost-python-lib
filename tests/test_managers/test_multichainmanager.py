import unittest

from chainpy.eth.managers.consts import *
from chainpy.eth.managers.multichainmanager import MultiChainManager
from tests.rpcendpointmock.rpcserver import MOCK_CHAIN_ID, ENDPOINT_URL
from tests.rpcendpointmock.util import *


class TestMultiChainManager(unittest.TestCase):
    def setUp(self) -> None:
        # launch mocking server
        self.server_launch_file_name = "../rpcendpointmock/rpcserver.py"
        launch_mock_server(self.server_launch_file_name)

        self.cli = MultiChainManager.from_config_files("../configs-event-test/entity.test.json")

        self.chain_name1 = "BFC_TEST"
        self.chain_name2 = "TestChain"
        self.dummy_private_key = "0x01"
        self.expected_address = "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"

    def tearDown(self) -> None:
        result = kill_by_file_name(self.server_launch_file_name)
        print("server down") if result else print("No server")

    def test_cli_init(self):
        # Allow MultiChainManager without account
        self.assertIsNone(self.cli.active_account)
        # When the MultiChainManager has an account, all the Chain Managers inside have the same account.
        self.cli.set_account(self.dummy_private_key)

        self.assertEqual(self.cli.supported_chain_list, [self.chain_name1, self.chain_name2])
        self.assertEqual(self.cli.multichain_config, {"chain_monitor_period_sec": 20})

        for chain_name in self.cli.supported_chain_list:
            chain_manager = self.cli.get_chain_manager_of(chain_name)

            self.assertEqual(chain_manager.address, self.expected_address)

            if chain_manager.chain_name == self.chain_name1:
                self.assertEqual(chain_manager.chain_id, int("0xbfc0", 16))
                self.assertTrue(isinstance(chain_manager.url, str))
                self.assertEqual(chain_manager.resend_delay_sec, 180)
                expected_tx_commit_time = 3 * (5 + 2)  # see, tests/configs-event-test/entity.test.json - $.BFC_TEST
                self.assertEqual(chain_manager.tx_commit_time_sec, expected_tx_commit_time)

                # see, tests/configs-event-test/entity.test.json - $.BFC_TEST.fee_config
                self.assertEqual(chain_manager.fee_config.type, 2)
                self.assertEqual(chain_manager.fee_config.type, chain_manager.tx_type)
                self.assertEqual(chain_manager.fee_config.max_gas_price, 5000000000000)
                self.assertEqual(chain_manager.fee_config.max_priority_price, 1000000000000)
                self.assertIsNone(chain_manager.fee_config.gas_price)

            elif chain_manager.chain_name == self.chain_name2:
                self.assertTrue(chain_manager.chain_id, int(MOCK_CHAIN_ID, 16))
                self.assertEqual(chain_manager.url, ENDPOINT_URL)
                self.assertEqual(chain_manager.resend_delay_sec, 3)
                expected_tx_commit_time = (
                        DEFAULT_BLOCK_PERIOD_SECS * (DEFAULT_RPC_TX_BLOCK_DELAY + DEFAULT_BLOCK_AGING_BLOCKS)
                )
                self.assertEqual(chain_manager.tx_commit_time_sec, expected_tx_commit_time)

                # Set to default config if config does not have fee information
                self.assertEqual(chain_manager.fee_config.type, 0)
                self.assertEqual(chain_manager.fee_config.type, chain_manager.tx_type)
                self.assertEqual(chain_manager.fee_config.gas_price, 2 ** 255 - 1)
                self.assertIsNone(chain_manager.fee_config.max_gas_price)
                self.assertIsNone(chain_manager.fee_config.max_priority_price)
            else:
                raise Exception("Not supported chain: {}".format(chain_name))

    def test_interaction_with_contracts(self):
        contract_from_chain1 = self.cli.get_contract_obj_on(self.chain_name1, "test_contract1")
        self.assertEqual(contract_from_chain1.address, "0x8Af2242724343Bd203B372F492d64AA8B0b0fFF2")
        self.assertEqual(contract_from_chain1.contract_name, "test_contract1")

        contract_from_chain2 = self.cli.get_contract_obj_on(self.chain_name2, "test_contract1")
        self.assertIsNone(contract_from_chain2)
