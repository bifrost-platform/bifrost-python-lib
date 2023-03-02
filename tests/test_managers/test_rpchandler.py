import os
import unittest
from time import sleep

from chainpy.eth.managers.consts import *
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.hexbytes import EthHashBytes, EthAddress
from chainpy.eth.ethtype.transaction import EthTransaction
from chainpy.eth.managers.exceptions import RpcOutOfStatusCode, RpCMaxRetry
from chainpy.eth.managers.rpchandler import EthRpcClient

from tests.rpcendpointmock.procutil import kill_by_file_name
from tests.rpcendpointmock.rpcserver import *


class TestContractHandler(unittest.TestCase):
    def setUp(self) -> None:
        # launch mocking server
        self.server_launch_file_name = "../rpcendpointmock/rpcserver.py"
        self.launch_mock_server()

        self.cli = EthRpcClient.from_config_files(
            "../configs-event-test/entity.test.json"
        )
        self.cli.url = ENDPOINT_URL
        self.block_hash = EthHashBytes(TEST_BLOCK_HASH)
        self.tx_hash = EthHashBytes(TEST_TRANSACTION_HASH)
        self.tx_hash_waiting = EthHashBytes(TEST_ADDITIONAL_TX_HASH)

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
        self.assertEqual(self.cli.chain_id, int(MOCK_CHAIN_ID, 16))
        self.assertEqual(self.cli.url, ENDPOINT_URL)
        self.assertEqual(self.cli.chain_name, "RESERVED_01")
        self.assertEqual(self.cli.resend_delay_sec, 3)

        expected_tx_commit_time = DEFAULT_BLOCK_PERIOD_SECS * (DEFAULT_RPC_TX_BLOCK_DELAY + DEFAULT_BLOCK_AGING_BLOCKS)
        self.assertEqual(self.cli.tx_commit_time_sec, expected_tx_commit_time)

    def test_send_request_base(self):
        result = self.cli.send_request("eth_chainId", [])
        self.assertEqual(result, MOCK_CHAIN_ID)

        self.assertRaises(Exception, self.cli.send_request, "eth_chainI", [])
        self.assertRaises(RpcOutOfStatusCode, self.cli.send_request_base, "server_error_503", [])
        self.assertRaises(RpcOutOfStatusCode, self.cli.send_request_base, "server_error_429", [])
        self.assertRaises(RpcOutOfStatusCode, self.cli.send_request_base, "server_error_404", [])

    def test_send_request(self):
        self.assertRaises(RpcOutOfStatusCode, self.cli.send_request, "server_error_503", [], resend_on_fail=False)

        before_call = self.cli.call_num
        self.assertRaises(RpCMaxRetry, self.cli.send_request, "server_error_503", [], resend_on_fail=True)
        self.assertEqual(self.cli.call_num - before_call, RPC_MAX_RESEND_ITER)

    def test_get_latest_block_number(self):
        latest_height = self.cli.eth_get_latest_block_number()
        self.assertEqual(latest_height, int(MOCK_LATEST_HEIGHT, 16))

        matured_latest_height = self.cli.eth_get_latest_block_number(matured_only=True)
        self.assertEqual(matured_latest_height, int(MOCK_LATEST_HEIGHT, 16) - self.cli.block_aging_period)

    def test_get_block(self):
        latest_height = int(MOCK_LATEST_HEIGHT, 16)

        # get_block with no option
        block = self.cli.eth_get_latest_block()
        self.assertEqual(block.number, latest_height)

        # get_block w/ verbose option
        block = self.cli.eth_get_latest_block(verbose=True)
        tx = block.transactions[0]
        self.assertEqual(tx.block_number, latest_height)
        self.assertTrue(isinstance(tx, EthTransaction))

        # get_block with matured_only option - returns latest and matured block
        block = self.cli.eth_get_latest_block(matured_only=True)
        self.assertEqual(block.number, latest_height - self.cli.block_aging_period)

        # get_block_by_height w/o matured_only option
        block = self.cli.eth_get_block_by_height(latest_height)
        self.assertEqual(block.number, latest_height)

        # get_block_by_height w/ matured_only option
        # block is None, that's why, the latest height is not matured.
        block = self.cli.eth_get_block_by_height(latest_height, matured_only=True)
        self.assertIsNone(block)

        # get_block_by_hash w/o matured_only option
        block = self.cli.eth_get_block_by_hash(self.block_hash)
        self.assertEqual(block.number, latest_height)

        # get_block_by_hash w/ matured_only option
        # block is None, that's why, the block exists but is not matured.
        block = self.cli.eth_get_block_by_hash(self.block_hash, matured_only=True)
        self.assertIsNone(block)

        # get_block_by_height w/o matured_only option
        block = self.cli.eth_get_block_by_height(TEST_HEIGHT)
        self.assertEqual(block.number, latest_height)

        # get_block_by_height w/o matured_only option
        # block is None, that's why, the block exists but is not matured.
        block = self.cli.eth_get_block_by_height(TEST_HEIGHT, matured_only=True)
        self.assertIsNone(block)

    def test_get_transaction(self):
        latest_height = int(MOCK_LATEST_HEIGHT, 16)

        # get_transaction_by_hash with no option
        tx = self.cli.eth_get_transaction_by_hash(self.tx_hash)
        self.assertEqual(tx.block_number, latest_height)

        # get_transaction_by_hash w/ matured_only option
        # transaction is None, that's why, the transaction exists but is not matured.
        tx = self.cli.eth_get_transaction_by_hash(self.tx_hash, matured_only=True)
        self.assertIsNone(tx)

        # get_transaction_by_height_and_index with no option
        tx = self.cli.eth_get_transaction_by_height_and_index(TEST_HEIGHT, TEST_TRANSACTION_INDEX)
        self.assertEqual(tx.block_number, latest_height)

        # get_transaction_by_height_and_index w/ matured_only option
        tx = self.cli.eth_get_transaction_by_height_and_index(TEST_HEIGHT, TEST_TRANSACTION_INDEX, matured_only=True)
        self.assertIsNone(tx)

    def test_get_receipt(self):
        latest_height = int(MOCK_LATEST_HEIGHT, 16)

        # get_receipt_without_wait with no option
        receipt = self.cli.eth_receipt_without_wait(self.tx_hash)
        self.assertEqual(receipt.block_number, latest_height)
        self.assertEqual(receipt.transaction_hash, self.tx_hash)

        # get_receipt_without_wait w/ matured_only option
        receipt = self.cli.eth_receipt_without_wait(self.tx_hash, matured_only=True)
        self.assertIsNone(receipt)

        # get_receipt_with_wait, it uses GET_RECEIPT_WAIT_ITER requests
        before_call = self.cli.call_num
        receipt = self.cli.eth_receipt_with_wait(self.tx_hash_waiting)
        self.assertTrue(isinstance(receipt.transaction_hash, EthHashBytes))
        self.assertEqual(self.cli.call_num - before_call, GET_RECEIPT_WAIT_ITER)

    def test_get_balance(self):
        balance = self.cli.eth_get_balance(EthAddress("0x71480ef89538d182241039e01808f639bf0416be"), hex(1000))
        self.assertEqual(balance.int(), 1000000000000000000)
        self.assertTrue(isinstance(balance, EthAmount))

        balance = self.cli.eth_get_balance(EthAddress("0x71480ef89538d182241039e01808f639bf0416be"), 1000)
        self.assertEqual(balance.int(), 1000000000000000000)
        self.assertTrue(isinstance(balance, EthAmount))
