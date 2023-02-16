from typing import List, Optional, Dict, Any, Union

from .utils import merge_dict
from bridgeconst.consts import Chain

from ..ethtype.chaindata import EthLog
from ..ethtype.contract import EthContract
from ..ethtype.exceptions import RpcExceedRequestTime
from ..ethtype.hexbytes import EthAddress, EthHashBytes

from .eventobj import DetectedEvent
from .rpchandler import EthRpcClient, DEFAULT_RECEIPT_MAX_RETRY, DEFAULT_BLOCK_PERIOD_SECS, \
    DEFAULT_BLOCK_AGING_BLOCKS, DEFAULT_RPC_DOWN_ALLOW_SECS, DEFAULT_RPC_TX_BLOCK_DELAY

DEFAULT_LATEST_HEIGHT = 0
DEFAULT_MAX_LOG_NUM = 1000


class EthContractHandler(EthRpcClient):
    def __init__(
            self,
            url_with_access_key: str,
            contracts: List[dict],
            chain_index: Chain,
            abi_dir: str = None,
            receipt_max_try: int = DEFAULT_RECEIPT_MAX_RETRY,
            block_period_sec: int = DEFAULT_BLOCK_PERIOD_SECS,
            block_aging_period: int = DEFAULT_BLOCK_AGING_BLOCKS,
            rpc_server_downtime_allow_sec: int = DEFAULT_RPC_DOWN_ALLOW_SECS,
            transaction_commit_multiplier: int = DEFAULT_RPC_TX_BLOCK_DELAY,
            events: List[dict] = None,
            latest_height: int = DEFAULT_LATEST_HEIGHT,
            max_log_num: int = DEFAULT_MAX_LOG_NUM
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

        self._matured_latest_height = DEFAULT_LATEST_HEIGHT if latest_height is None else latest_height
        self._max_log_num = DEFAULT_MAX_LOG_NUM if max_log_num is None else max_log_num

        self._contracts = dict()
        self._event_db: Dict[str, List[Dict[str, Any]]] = dict()

        for contract_dict in contracts:
            # determine abi_path of the contract
            abi_path = contract_dict.get("abi_path")
            if abi_path is None:
                abi_path = abi_dir + contract_dict.get("abi_file")

            # init contract_obj of the contract
            contract_obj = EthContract.from_abi_file(contract_dict["name"], contract_dict["address"], abi_path)

            # assume that every contract has a different name.
            contract_name = contract_dict["name"]
            if self._contracts.get(contract_name) is not None:
                raise Exception("Collision contract names")

            # store contract obj by contract_name
            self._contracts[contract_name] = contract_obj

        if events is not None and isinstance(events, list):
            for event in events:
                # Check that each event belongs to a known contract.
                event_name, contract_name = event["event_name"], event["contract_name"]
                if self._contracts.get(contract_name) is None:
                    raise Exception("Event of unknown contract: {}".format(event))
                data = {
                    "contract": self._contracts[contract_name],
                    "topic": self._contracts[contract_name].get_method_abi(event_name).get_topic()
                }
                if self._event_db.get(event_name) is None:
                    self._event_db[event_name] = [data]
                else:
                    self._event_db[event_name].append(data)

    @classmethod
    def from_config_dict(cls, config: dict, private_config: dict = None, chain_index: Chain = None):
        merged_config = merge_dict(config, private_config)
        if merged_config.get("chain_name") is not None:
            # In the case of being entered chain_config
            chain_index = Chain.from_name(merged_config.get("chain_name").upper())
            chain_config = merged_config
        elif chain_index is not None:
            # In the case of being entered multichain_config
            chain_config = merged_config.get(chain_index.name)
            if chain_config is None:
                # there is no target chain-config in multichain_config
                raise Exception("should be inserted chain config")
        else:
            raise Exception("Can not determine the target chain")

        return cls(
            url_with_access_key=chain_config["url_with_access_key"],
            contracts=chain_config["contracts"],
            chain_index=chain_index,
            abi_dir=chain_config.get("abi_dir"),
            receipt_max_try=chain_config.get("receipt_max_try"),
            block_period_sec=chain_config.get("block_period_sec"),
            block_aging_period=chain_config.get("block_aging_period"),
            rpc_server_downtime_allow_sec=chain_config.get("rpc_server_downtime_allow_sec"),

            events=chain_config.get("events"),
            latest_height=chain_config.get("bootstrap_latest_height"),
            max_log_num=chain_config.get("max_log_num")
        )

    @property
    def latest_height(self) -> int:
        return self._matured_latest_height

    @latest_height.setter
    def latest_height(self, height: int):
        self._matured_latest_height = height

    @property
    def max_log_num(self) -> int:
        return self._max_log_num

    def get_contract_by_name(self, contract_name: str) -> Optional[EthContract]:
        return self._contracts.get(contract_name)

    def get_contract_by_addr(self, contract_addr: EthAddress) -> Optional[EthContract]:
        for contract in self._contracts.values():
            if contract.address == contract_addr:
                return contract
        return None

    def get_contracts_by_event_name(self, event_name: str) -> List[EthContract]:
        data = self._event_db.get(event_name)
        if data is None:
            return list()
        return [data["contract"] for data in self._event_db[event_name]]

    def get_contracts_name_by_event_name(self, event_name: str) -> List[str]:
        contracts = self.get_contracts_by_event_name(event_name)
        return [contract.contract_name for contract in contracts]

    def get_event_names(self) -> List[str]:
        return list(self._event_db.keys())

    def get_topic_by_event_name(self, event_name: str) -> EthHashBytes:
        data = self._event_db.get(event_name)
        return data[0]["topic"]

    def get_every_topics(self) -> List[EthHashBytes]:
        topics = list()
        for data in self._event_db.values():
            for item in data:
                topics.append(item["topic"])
        return sorted(list(set(topics)))

    def get_event_name_by_topic(self, topic: EthHashBytes) -> Optional[str]:
        topic_hex = topic.hex()
        for event_name, data in self._event_db.items():
            for item in data:
                if item["topic"] == topic_hex:
                    return event_name
        return None

    def get_emitter_addresses(self, event_name: str = None) -> List[EthAddress]:
        addresses = list()
        for _event_name, data in self._event_db.items():
            if event_name is not None and event_name != _event_name:
                continue
            for item in data:
                addresses.append(item["contract"].address)
        return sorted(list(set(addresses)))

    def _get_logs(
            self, from_block: int, to_block: int,
            emitter_addresses: List[EthAddress],
            topics: List[Union[EthHashBytes, List[EthHashBytes]]]) -> List[EthLog]:
        """
        Wrapper method of eth_get_logs.
        If the eth_get_logs exceeds request time, call twice with half range.
        """
        try:
            raw_logs = self.eth_get_logs(from_block, to_block, emitter_addresses, [topics])
            return raw_logs
        except RpcExceedRequestTime:
            self._max_log_num = self._max_log_num // 2
            delta_half = (to_block - from_block) // 2
            raw_logs = self._get_logs(from_block, from_block + delta_half, emitter_addresses, topics)
            raw_logs += self._get_logs(from_block + delta_half + 1, to_block, emitter_addresses, topics)
            return raw_logs

    def _check_fetched_event(
            self, logs: List[EthLog], emitter_addresses: List[EthAddress]) -> List[DetectedEvent]:
        historical_logs = list()
        for log in logs:
            # check weather the log was emitted by one of target contracts
            fetched_topic, fetched_contract_address = EthHashBytes(log.topics[0]), EthAddress(log.address)
            if fetched_contract_address not in emitter_addresses:
                raise Exception("Topic and Contract address in the event are not matched.")

            # Find information related to the event log.
            contract_name = self.get_contract_by_addr(fetched_contract_address).contract_name
            event_name = self.get_event_name_by_topic(fetched_topic)

            # build event object and collect it (to return)
            detected_event = DetectedEvent(self.chain, contract_name, event_name, log)
            historical_logs.append(detected_event)

        return historical_logs

    def collect_event_in_limited_range(self, event_name: str, from_block: int, to_block: int) -> List[DetectedEvent]:
        """ Collect the specific event """
        if to_block < from_block:
            raise Exception("from_block is bigger than to_block")
        emitter_addresses, topic = self.get_emitter_addresses(event_name), self.get_topic_by_event_name(event_name)
        logs = self._get_logs(from_block, to_block, emitter_addresses, [topic])
        return self._check_fetched_event(logs, emitter_addresses)

    def collect_every_event_in_limited_range(self, from_block: int, to_block: int) -> List[DetectedEvent]:
        """ Collect every event specified in config. """
        if to_block < from_block:
            raise Exception("from_block is bigger than to_block")

        emitter_addresses, event_topics = self.get_emitter_addresses(), self.get_every_topics()
        logs = self._get_logs(from_block, to_block, emitter_addresses, event_topics)

        return self._check_fetched_event(logs, emitter_addresses)

    def collect_every_event(
            self, from_block: int, to_block: int) -> List[DetectedEvent]:
        """  collect the event in specific range (at the single blockchain) """
        if to_block < from_block:
            raise Exception("from_block is bigger than to_block")

        # (Note) include both from_block and to_block
        num_slices, remainder = divmod(to_block - from_block + 1, self._max_log_num)
        if remainder != 0:
            num_slices += 1

        historical_logs, prev_height = list(), from_block
        for i in range(num_slices):
            next_height = min(prev_height + self._max_log_num, to_block)
            historical_logs += self.collect_every_event_in_limited_range(prev_height, next_height)
            if next_height == to_block:
                break
            prev_height = next_height + 1
        return historical_logs

    def collect_unchecked_single_chain_events(self, matured_only: bool = True) -> List[DetectedEvent]:
        """ collect every type of events until the current block (at the single blockchain) """
        current_height = self.eth_get_latest_block_number(matured_only=matured_only)

        if self.latest_height + 1 > current_height:
            return list()

        historical_events = self.collect_every_event(self.latest_height + 1, current_height)
        self.latest_height = current_height

        return historical_events
