import unittest

from bridgeconst.consts import Chain

from chainpy.eth.ethtype.hexbytes import EthHashBytes, EthAddress, EthHexBytes
from chainpy.eth.ethtype.transaction import EthTransaction
from chainpy.eth.managers.contracthandler_staged import EthContractHandler


class TestTransaction(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = EthContractHandler.from_config_files(
            "./configs-event-test/entity.test.json",
            chain_index=Chain.BFC_TEST
        )
        self.contract1 = self.cli.get_contract_by_name("test_contract1")
        self.contract2 = self.cli.get_contract_by_name("test_contract2")

    def test_collect_events_from_two_contracts(self):
        current_height = self.cli.eth_get_latest_block_number()
        topic1 = self.contract1.get_method_abi("TestEvent1").get_topic()
        topic2 = self.contract1.get_method_abi("TestEvent2").get_topic()

        result = self.cli.eth_get_logs(
            current_height - 1000, current_height,
            [self.contract1.address, self.contract2.address],
            [[topic1, topic2]]
        )
        print("num: {}".format(len(result)))
        for log in result:
            print(log)
