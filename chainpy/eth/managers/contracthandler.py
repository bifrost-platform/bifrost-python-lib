import unittest
from typing import List, Optional

from .configs import merge_dict
from ..ethtype.consts import ChainIndex
from ..ethtype.contract import EthContract
from ..ethtype.exceptions import RpcExceedRequestTime
from ..ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes

from .eventobj import DetectedEvent
from .rpchandler import EthRpcClient, DEFAULT_RECEIPT_MAX_RETRY, DEFAULT_BLOCK_PERIOD_SECS, \
    DEFAULT_BLOCK_AGING_BLOCKS, DEFAULT_RPC_DOWN_ALLOW_SECS, DEFAULT_RPC_COMMIT_TIME_MULTIPLIER
from ..ethtype.transaction import EthTransaction


class EthContractHandler(EthRpcClient):
    def __init__(
            self,
            url_with_access_key: str,
            contracts: List[dict],
            chain_index: ChainIndex,
            abi_dir: str = None,
            receipt_max_try: int = DEFAULT_RECEIPT_MAX_RETRY,
            block_period_sec: int = DEFAULT_BLOCK_PERIOD_SECS,
            block_aging_period: int = DEFAULT_BLOCK_AGING_BLOCKS,
            rpc_server_downtime_allow_sec: int = DEFAULT_RPC_DOWN_ALLOW_SECS,
            transaction_commit_multiplier: int = DEFAULT_RPC_COMMIT_TIME_MULTIPLIER,
            events: List[dict] = None,
            latest_height: int = 0,
            max_log_num: int = 1000
    ):
        super().__init__(
            url_with_access_key,
            chain_index,
            receipt_max_try,
            block_period_sec,
            block_aging_period,
            rpc_server_downtime_allow_sec,
            transaction_commit_multiplier
        )

        self._matured_latest_height = latest_height if latest_height is None else 0
        self.__max_log_num =  1000 if max_log_num is None else max_log_num

        self._contracts = dict()
        self._contract_name_by_event_name = dict()
        self._event_name_by_topic = dict()

        for contract_dict in contracts:
            abi_path = contract_dict.get("abi_path")
            if abi_path is None:
                abi_path = abi_dir + contract_dict.get("abi_file")
            contract_obj = EthContract.from_abi_file(contract_dict["name"], contract_dict["address"], abi_path)
            self._contracts[contract_dict["name"]] = contract_obj

        if events is not None and isinstance(events, list):
            for event in events:
                # parse contract's address and abi
                event_name = event["event_name"]
                self._contract_name_by_event_name[event_name] = event["contract_name"]

                contract = self._contracts[event["contract_name"]]
                topic = contract.get_method_abi(event_name).get_topic()
                self._event_name_by_topic[topic.hex()] = event_name

    @classmethod
    def from_config_dict(cls, config: dict, private_config: dict = None, chain_index: ChainIndex = None):
        merged_config = merge_dict(config, private_config)

        if merged_config.get("chain_name") is None and chain_index is None:
            # multichain config and no chain index
            raise Exception("should be inserted chain config")

        if chain_index is None:
            # in case of being inserted a chain config without chain index
            chain_index = ChainIndex[merged_config["chain_name"].upper()]

        if merged_config.get("chain_name") is None:
            merged_config = merged_config[chain_index.name.lower()]
        return cls(
            merged_config["url_with_access_key"],
            merged_config["contracts"],
            chain_index,
            merged_config.get("abi_dir"),
            merged_config.get("receipt_max_try"),
            merged_config.get("block_period_sec"),
            merged_config.get("block_aging_period"),
            merged_config.get("rpc_server_downtime_allow_sec"),

            merged_config.get("events"),
            merged_config.get("bootstrap_latest_height"),
            merged_config.get("max_log_num")
        )

    @property
    def latest_height(self) -> int:
        return self._matured_latest_height

    @latest_height.setter
    def latest_height(self, height: int):
        self._matured_latest_height = height

    @property
    def max_log_num(self) -> int:
        return self.__max_log_num

    def get_contract_by_name(self, contract_name: str) -> Optional[EthContract]:
        return self._contracts.get(contract_name)

    def get_contract_by_addr(self, contract_addr: EthAddress) -> Optional[EthContract]:
        for contract in self._contracts.values():
            if contract.address == contract_addr:
                return contract
        return None

    def get_contract_by_event_name(self, event_name: str) -> Optional[EthContract]:
        contract_name = self._contract_name_by_event_name.get(event_name)
        return self.get_contract_by_name(contract_name)

    def get_contract_name_by_event_name(self, event_name: str) -> str:
        return self._contract_name_by_event_name[event_name]

    def get_event_names(self) -> List[str]:
        return list(self._contract_name_by_event_name.keys())

    def get_event_name_by_topic(self, topic: EthHashBytes) -> str:
        return self._event_name_by_topic[topic.hex()]

    def get_all_emitters(self) -> List[EthAddress]:
        addresses = list()
        for event_name, contract_name in self._contract_name_by_event_name.items():
            contract_address = self._contracts[contract_name].address
            addresses.append(contract_address)
        return addresses

    def get_all_topics(self) -> List[EthHashBytes]:
        return [EthHashBytes(topic) for topic in self._event_name_by_topic.keys()]

    def small_ranged_collect_events(self, event_name: str, from_block: int, to_block: int) -> List[DetectedEvent]:
        if to_block < from_block:
            return list()

        emitter = self.get_contract_by_event_name(event_name)
        if emitter is None:
            return list()
        emitter_addr = emitter.address
        event_topic = emitter.get_method_abi(event_name).get_topic()

        try:
            raw_logs = self.eth_get_logs(from_block, to_block, [emitter_addr], [event_topic])
        except RpcExceedRequestTime:
            self.__max_log_num = self.__max_log_num // 2
            delta_half = (to_block - from_block) // 2
            detected_events = self.small_ranged_collect_events(event_name, from_block, from_block + delta_half)
            detected_events += self.small_ranged_collect_events(event_name, from_block + delta_half + 1, to_block)
            return detected_events

        historical_logs = list()
        for raw_log in raw_logs:
            # loads information related to the log
            topic, contract_address = EthHashBytes(raw_log.topics[0]), EthAddress(raw_log.address)
            event_name = self.get_event_name_by_topic(topic)
            contract_name = self.get_contract_name_by_event_name(event_name)

            # check weather the log was emitted by one of target contracts
            if emitter_addr != contract_address:
                raise Exception("Topic and Contract address in the event are not matched.")
            # build event object and collect it (to return)
            detected_event = DetectedEvent(self.chain_index, contract_name, event_name, raw_log)
            historical_logs.append(detected_event)

        self.latest_height = to_block + 1

        return historical_logs

    def ranged_collect_events(self,
                              event_name: str,
                              from_block: int,
                              to_block: int = None) -> List[DetectedEvent]:
        """  collect the event in specific range (at the single blockchain) """
        to_block = self.eth_get_matured_block_number() if to_block is None else to_block

        if to_block < from_block:
            return list()

        delta_blocks = to_block - from_block
        loop_num = delta_blocks // self.__max_log_num
        if delta_blocks % self.__max_log_num != 0:
            loop_num += 1

        historical_logs = list()
        prev_height = from_block
        for i in range(loop_num):
            next_height = min(prev_height + self.__max_log_num, to_block)
            historical_logs += self.small_ranged_collect_events(event_name, prev_height, next_height)
            if next_height == to_block:
                break
            prev_height = next_height + 1
        return historical_logs

    def collect_unchecked_single_chain_events(self) -> List[DetectedEvent]:
        """ collect every type of events until the current block (at the single blockchain) """
        previous_matured_max_height = self.latest_height
        current_matured_max_height = self.eth_get_matured_block_number()
        if current_matured_max_height <= previous_matured_max_height:
            return list()

        historical_events = list()
        for event_name in self._contract_name_by_event_name.keys():
            historical_events += self.ranged_collect_events(
                event_name,
                previous_matured_max_height,
                current_matured_max_height
            )

        return historical_events


class TestTransaction(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = EthContractHandler.from_config_files(
            "../configs/entity.relayer.json",
            "../configs/entity.relayer.private.json",
            chain_index=ChainIndex.BIFROST
        )
        self.target_tx_hash = EthHashBytes(0xfb6ceb412ae267643d45b28516565b1ab07f4d16ade200d7e432be892add1448)
        self.serialized_tx = "0xf90153f9015082bfc082301f0186015d3ef7980183036e54947abd332cf88ca31725fffb21795f90583744535280b901246196d920000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000001524d2eadae57a7f06f100476a57724c1295c8fe99db52b6af3e3902cc8210e97000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000b99000000000000000000000000000000000000000000000000000000000000000001000000000000000000062bf8e916ee7d6d68632b2ee0d6823a5c9a7cd69c874ec0"

    def test_serialize_tx_from_rpc(self):
        transaction = self.cli.eth_get_transaction_by_hash(self.target_tx_hash)
        self.assertEqual(transaction.serialize(), self.serialized_tx)

    def test_serialize_tx_built(self):
        tx_obj: EthTransaction = EthTransaction.init(
            int("0xbfc0", 16),  # chain_id
            EthAddress("0x7abd332cf88ca31725fffb21795f905837445352"),  # to
            data=EthHexBytes("0x6196d920000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000001524d2eadae57a7f06f100476a57724c1295c8fe99db52b6af3e3902cc8210e97000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000b99000000000000000000000000000000000000000000000000000000000000000001000000000000000000062bf8e916ee7d6d68632b2ee0d6823a5c9a7cd69c874e")
        )
        tx_obj.set_nonce(int("0x301f", 16)).set_gas_prices(int("0x015d3ef79801", 16), int("0x01", 16)).set_gas_limit(int("0x036e54", 16))
        self.assertEqual(tx_obj.serialize(), self.serialized_tx)
