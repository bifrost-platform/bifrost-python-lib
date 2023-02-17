import unittest
from typing import List

from bridgeconst.consts import Chain

from chainpy.eth.ethtype.chaindata import EthLog
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes
from chainpy.eth.managers.contracthandler import EthContractHandler


class TestContractHandler(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = EthContractHandler.from_config_files(
            "./configs-event-test/entity.test.json",
            chain_index=Chain.BFC_TEST
        )
        self.contract_addr1 = EthAddress(0x8Af2242724343Bd203B372F492d64AA8B0b0fFF2)
        self.contract_name1 = "test_contract1"
        self.event_name1 = "TestEvent1"
        self.topic1 = EthHashBytes("0x8842899e9be9f8182eb6ede21c9a5b3036330f25eb83a84c2542a75cdb381782")

        self.contract_addr2 = EthAddress(0xDFA467cf8e57699aF7ffd1adC8775d798756352E)
        self.contract_name2 = "test_contract2"
        self.event_name2 = "TestEvent2"
        self.topic2 = EthHashBytes("0xc98f871161824f7ebd6f185b9c0d6ec054c7d5c99a55182109148b69f67c59ec")

        self.from_block, self.to_block = 3610000, 3636650

        self.cli.latest_height = self.from_block

    def test_properties(self):
        self.assertEqual(self.cli.latest_height, 2883)
        self.assertEqual(self.cli.max_log_num, 2000)

    def test_query_methods(self):
        contract1 = self.cli.get_contract_by_name(self.contract_name1)
        self.assertEqual(contract1.contract_name, self.contract_name1)

        contract2 = self.cli.get_contract_by_addr(self.contract_addr2)
        self.assertEqual(contract2.contract_name, self.contract_name2)

        contracts = self.cli.get_contracts_by_event_name(self.event_name1)
        for contract in contracts:
            self.assertTrue(contract.contract_name in [self.contract_name1, self.contract_name2])

        contract_names = self.cli.get_contracts_name_by_event_name(self.event_name1)
        for name in contract_names:
            self.assertTrue(name in [self.contract_name1, self.contract_name2])

        event_names = self.cli.get_event_names()
        self.assertEqual(event_names, [self.event_name1, self.event_name2])

        topic = self.cli.get_topic_by_event_name(self.event_name1)
        self.assertEqual(topic, self.topic1)

        event_name = self.cli.get_event_name_by_topic(topic)
        self.assertEqual(event_name, self.event_name1)

        contract_addresses = self.cli.get_emitter_addresses()
        self.assertEqual(contract_addresses, [self.contract_addr1, self.contract_addr2])

        topics = self.cli.get_every_topics()
        self.assertEqual(topics, [self.topic1, self.topic2])

    def test_collect_event_in_limited_range(self):
        detected_events = self.cli.collect_event_in_limited_range(self.event_name1, self.from_block, self.to_block)
        for detected_event in detected_events:
            self.assertEqual(detected_event.event_name, self.event_name1)

        detected_events = self.cli.collect_event_in_limited_range(self.event_name2, self.from_block, self.to_block)
        for detected_event in detected_events:
            self.assertEqual(detected_event.event_name, self.event_name2)

    def _check_logs(self, logs: List[EthLog]):
        self.assertEqual(len(logs), 8)
        for log in logs:
            self.assertTrue(log.contract_name in [self.contract_name1, self.contract_name2])
            self.assertTrue(log.topic in [self.topic1, self.topic2])
            self.assertTrue(log.event_name in [self.event_name1, self.event_name2])
            self.assertTrue(self.from_block <= log.block_number <= self.to_block)

    def test_collect_every_event_in_limited_range(self):
        before_call_num = self.cli.call_num
        logs = self.cli.collect_every_event_in_limited_range(self.from_block, self.to_block)
        self._check_logs(logs)
        self.assertEqual(self.cli.call_num - before_call_num, 2)

    def test_collect_every_event(self):
        self.assertNotEqual(self.to_block, self.cli.latest_height)

        before_call_num = self.cli.call_num
        logs = self.cli.collect_every_event(self.from_block, self.to_block)
        self._check_logs(logs)
        self.assertEqual(self.cli.call_num - before_call_num, 28)

        self.assertNotEqual(self.to_block, self.cli.latest_height)

    def test_collect_unchecked_single_chain_events(self):
        before_height = self.cli.latest_height
        logs = self.cli.collect_unchecked_single_chain_events(matured_only=True)
        self._check_logs(logs)
        self.assertTrue(before_height < self.cli.latest_height)
