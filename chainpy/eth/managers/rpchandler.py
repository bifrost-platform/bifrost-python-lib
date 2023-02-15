import json
import unittest
from json import JSONDecodeError

import requests
import time
from typing import List, Optional, Union, Callable

from .exceptions import raise_integrated_exception, RpcOutOfStatusCode, RpcNoneResult, RpCMaxRetry
from .utils import merge_dict
from ..ethtype.amount import EthAmount
from bridgeconst.consts import Chain
from ..ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes
from ..ethtype.chaindata import EthBlock, EthReceipt, EthLog
from ..ethtype.exceptions import *
from ..ethtype.transaction import EthTransaction
from ...logger import global_logger
from ...prometheus_metric import PrometheusExporter

RPC_RETRY_MAX_RETRY_NUM = 20
RPC_RETRY_SLEEP_TIME_IN_SECS = 180
DEFAULT_RECEIPT_MAX_RETRY: int = 10
DEFAULT_BLOCK_PERIOD_SECS: int = 3
DEFAULT_BLOCK_AGING_BLOCKS: int = 1
DEFAULT_RPC_DOWN_ALLOW_SECS: int = 180
DEFAULT_RPC_TX_BLOCK_DELAY: int = 2


def _reduce_height_to_matured_height(matured_max_height: int, height: Union[int, str]) -> str:
    if height == "latest":
        height = 2 ** 256 - 1
    if isinstance(height, int):
        return hex(min(height, matured_max_height))
    raise Exception("height should be integer or \"latest\"")


def _hex_height_or_latest(height: Union[int, str] = "latest") -> str:
    if height == "latest":
        return height
    if isinstance(height, int):
        return hex(height)
    raise Exception("height should be integer or \"latest\"")


class EthRpcClient:
    """ Client class for Ethereum JSON RPC.

    The following methods have not yet been implemented
    - eth_newFilter
    - eth_getFilterChanges
    - eth_newBlockFilter
    - eth_getStorageAt
    - eth_getCode
    """

    def __init__(
            self,
            url_with_access_key: str,
            chain: Chain = Chain.NONE,
            receipt_max_try: int = DEFAULT_RECEIPT_MAX_RETRY,
            block_period_sec: int = DEFAULT_BLOCK_PERIOD_SECS,
            block_aging_period: int = DEFAULT_BLOCK_AGING_BLOCKS,
            rpc_server_downtime_allow_sec: int = DEFAULT_RPC_DOWN_ALLOW_SECS,
            transaction_block_delay: int = DEFAULT_RPC_TX_BLOCK_DELAY
    ):
        self.__chain = chain
        self.__url_with_access_key = url_with_access_key
        self.__receipt_max_try = DEFAULT_RECEIPT_MAX_RETRY if receipt_max_try is None else receipt_max_try
        self.__block_period_sec = DEFAULT_BLOCK_PERIOD_SECS if block_period_sec is None else block_period_sec
        self.__block_aging_period = DEFAULT_BLOCK_AGING_BLOCKS if block_aging_period is None else block_aging_period
        self.__rpc_server_downtime_allow_sec = DEFAULT_RPC_DOWN_ALLOW_SECS \
            if rpc_server_downtime_allow_sec is None else rpc_server_downtime_allow_sec
        self.__transaction_block_delay = DEFAULT_RPC_TX_BLOCK_DELAY \
            if transaction_block_delay is None else transaction_block_delay

        # check connection
        self.__chain_id: Optional[int] = None
        if self.__url_with_access_key:
            resp = self.send_request("eth_chainId", [])
            self.__chain_id = int(resp, 16)

    @classmethod
    def from_config_dict(cls, config: dict, private_config: dict = None, chain_index: Chain = None):
        merged_config = merge_dict(config, private_config)

        if merged_config.get("chain_name") is None and chain_index is None:
            # multichain config and no chain index
            raise Exception("should be inserted chain config")

        if chain_index is None:
            # in case of being inserted a chain config without chain index
            chain_index = Chain[merged_config["chain_name"].upper()]

        if merged_config.get("chain_name") is None:
            merged_config = merged_config[chain_index.name.upper()]

        return cls(
            merged_config["url_with_access_key"],
            chain_index,
            merged_config.get("receipt_max_try"),
            merged_config.get("block_period_sec"),
            merged_config.get("block_aging_period"),
            merged_config.get("rpc_server_downtime_allow_sec")
        )

    @classmethod
    def from_config_files(cls, config_file: str, private_config_file: str = None, chain_index: Chain = Chain.NONE):
        with open(config_file, "r") as f:
            config = json.load(f)
        if private_config_file is None:
            private_config = None
        else:
            with open(private_config_file, "r") as f:
                private_config = json.load(f)
        return cls.from_config_dict(config, private_config, chain_index)

    @property
    def url(self) -> str:
        return self.__url_with_access_key

    @property
    def tx_commit_time_sec(self) -> int:
        return self.__block_period_sec * (self.__transaction_block_delay + self.__block_aging_period)

    def send_request(self, method: str, params: list, cnt: int = 0) -> Optional[Union[dict, str]]:
        if cnt > RPC_RETRY_MAX_RETRY_NUM:
            raise RpCMaxRetry(self.chain, "Exceeded max re-try cnt")

        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        headers = {'Content-type': 'application/json'}
        try:
            PrometheusExporter.exporting_rpc_requested(self.chain)
            response = requests.post(self.url, json=body, headers=headers)

            code = response.status_code
            if code < 200 or 400 < code:
                PrometheusExporter.exporting_rpc_failed(self.chain)
                raise RpcOutOfStatusCode(self.chain, "code({}), msg({})".format(code, response.content))

        except Exception as e:
            PrometheusExporter.exporting_rpc_failed(self.chain)
            global_logger.formatted_log("RPCException", related_chain=self.__chain, msg=str(e))

            sleep_notify_msg = "re-tried after {} secs".format(self.__rpc_server_downtime_allow_sec)
            global_logger.formatted_log("RPCException", related_chain=self.__chain, msg=sleep_notify_msg)
            time.sleep(self.__rpc_server_downtime_allow_sec)

            resend_notify_msg = "re-send rpc request: {}".format(body)
            global_logger.formatted_log("RPCException", related_chain=self.__chain, msg=resend_notify_msg)
            return self.send_request(method, params)

        try:
            response_json = response.json()
        except JSONDecodeError:
            PrometheusExporter.exporting_rpc_failed(self.chain)
            global_logger.formatted_log("RPCJsonDecodeError", related_chain=self.__chain, msg=str(response.content))

            sleep_notify_msg = "re-tried after {} secs".format(self.__rpc_server_downtime_allow_sec)
            global_logger.formatted_log("RPCJsonDecodeError", related_chain=self.__chain, msg=sleep_notify_msg)

            time.sleep(RPC_RETRY_SLEEP_TIME_IN_SECS)

            resend_notify_msg = "re-send rpc request: {}".format(body)
            global_logger.formatted_log("RPCJsonDecodeError", related_chain=self.__chain, msg=resend_notify_msg)
            return self.send_request(method, params, cnt + 1)

        except Exception:
            # just defensive code
            raise Exception("Not handled error on {}: {}".format(self.chain.name, response.content))

        if "result" in list(response_json.keys()):
            return response_json["result"]

        # Evm error always gets caught here.
        PrometheusExporter.exporting_rpc_failed(self.chain)
        if "error" in list(response_json.keys()):
            raise_integrated_exception(self.chain, error_json=response_json["error"])
        else:
            raise Exception("Not handled error on {}: {}".format(self.chain.name, response.content))

    @property
    def chain(self) -> Chain:
        """ return chain index specified from the configuration. """
        return self.__chain

    @property
    def chain_id(self) -> int:
        """ return chain id emitted by the rpc node. """
        return self.__chain_id

    def _reduce_heights_to_matured_height(self, heights: Union[list, int, str]) -> Union[List[str], str]:
        """
        reduce heights whenever each height is bigger than matured height.
        note that matured height means the maximum confirmed block height.
        """
        latest_block_height = self.eth_get_latest_block_number()
        matured_max_height = latest_block_height - self.__block_aging_period

        if not isinstance(heights, list):
            # for single height
            return _reduce_height_to_matured_height(matured_max_height, heights)
        else:
            # for multi heights
            amended_heights = list()
            for height in heights:
                amended_height = _reduce_height_to_matured_height(matured_max_height, height)
                amended_heights.append(amended_height)
            return amended_heights

    def eth_get_latest_block_number(self) -> int:
        """ returns the latest block height. """
        resp = self.send_request("eth_blockNumber", list())
        return int(resp, 16)

    def eth_get_matured_block_number(self) -> int:
        """ queries the latest block height and returns matured block height."""
        latest_height = self.eth_get_latest_block_number()
        return latest_height - self.__block_aging_period

    def eth_get_latest_block(self, verbose: bool = False) -> EthBlock:
        resp = self.send_request("eth_getBlockByNumber", ["latest", verbose])
        return EthBlock.from_dict(resp)

    def eth_get_balance(self, address: EthAddress, height: Union[int, str] = "latest",
                        matured: bool = False) -> EthAmount:
        """ queries matured balance of the user. """
        if not isinstance(address, EthAddress):
            raise Exception("address type must be \"EthAddress\" type")
        if matured:
            height = self._reduce_heights_to_matured_height(height)
        resp = self.send_request("eth_getBalance", [address.hex(), height])
        return EthAmount(resp)

    def _get_block(self, method: str, params: list) -> Optional[EthBlock]:
        resp = self.send_request(method, params)
        return EthBlock.from_dict(resp)

    def _get_matured_block(self, method: str, params: list) -> Optional[EthBlock]:
        resp = self.send_request(method, params)
        fetched_block: EthBlock = EthBlock.from_dict(resp)
        if fetched_block.number > self.eth_get_matured_block_number():
            return None
        return fetched_block

    def eth_get_block_by_hash(self, block_hash: EthHashBytes, verbose: bool = False) -> Optional[EthBlock]:
        if not isinstance(block_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(block_hash))
        return self._get_block("eth_getBlockByHash", [block_hash.hex(), verbose])

    def eth_get_block_by_height(self, height: Union[int, str] = "latest", verbose: bool = False) -> Optional[EthBlock]:
        height_hex_or_latest = _hex_height_or_latest(height)
        return self._get_block("eth_getBlockByNumber", [height_hex_or_latest, verbose])

    def _get_transaction(self, method: str, params: list) -> Optional[EthTransaction]:
        resp = self.send_request(method, params)
        fetched_tx: EthTransaction = EthTransaction.from_dict(resp)
        if fetched_tx.block_number > self.eth_get_matured_block_number():
            return None
        return fetched_tx

    def eth_get_transaction_by_hash(self, tx_hash: EthHashBytes) -> Optional[EthTransaction]:
        if not isinstance(tx_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(tx_hash))
        return self._get_transaction("eth_getTransactionByHash", [tx_hash.hex()])

    def eth_get_transaction_by_height_and_index(self, height: int, tx_index: int) -> Optional[EthTransaction]:
        if not isinstance(height, int):
            raise EthTypeError(int, type(height))
        if not isinstance(tx_index, int):
            raise EthTypeError(int, type(tx_index))
        return self._get_transaction("eth_getTransactionByBlockNumberAndIndex", [hex(height), hex(tx_index)])

    def eth_get_transaction_by_hash_and_index(self,
                                              block_hash: EthHashBytes,
                                              tx_index: int) -> Optional[EthTransaction]:
        if not isinstance(block_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(block_hash))
        if not isinstance(tx_index, int):
            raise EthTypeError(int, type(tx_index))
        return self._get_transaction("eth_getTransactionByBlockHashAndIndex", [block_hash.hex(), hex(tx_index)])

    def _get_matured_receipt(self, tx_hash: EthHashBytes) -> Optional[EthReceipt]:
        resp = self.send_request('eth_getTransactionReceipt', [tx_hash.hex()])

        if resp is None:
            return None
        fetched_receipt: EthReceipt = EthReceipt.from_dict(resp)
        if fetched_receipt.block_number > self.eth_get_matured_block_number():
            return None
        return fetched_receipt

    def _get_receipt(self, tx_hash: EthHashBytes) -> Optional[EthReceipt]:
        resp = self.send_request('eth_getTransactionReceipt', [tx_hash.hex()])
        if resp is not None:
            return EthReceipt.from_dict(resp)

    def eth_receipt_without_wait(self, tx_hash: EthHashBytes, matured: bool = True) -> Optional[EthReceipt]:
        get_receipt_func: Callable = self._get_matured_receipt if matured else self._get_receipt
        return get_receipt_func(tx_hash)

    def eth_receipt_with_wait(self, tx_hash: EthHashBytes, matured: bool = True) -> Optional[EthReceipt]:
        get_receipt_func: Callable = self._get_matured_receipt if matured else self._get_receipt
        for i in range(self.__receipt_max_try):
            receipt = get_receipt_func(tx_hash)
            if receipt is not None:
                return receipt
            time.sleep(self.__block_period_sec / 2)  # wait half block
        return None

    def eth_get_logs(self,
                     from_block: int, to_block: int,
                     addresses: List[EthAddress],
                     topics: List[Union[EthHashBytes, List[EthHashBytes]]]) -> List[EthLog]:
        """ find logs of the event (which have topics) from multiple contracts """
        if from_block > to_block:
            raise Exception("from_block should be less than to_block")

        amended_block_nums = self._reduce_heights_to_matured_height([from_block, to_block])

        topic_hexes = list()
        for topic in topics:
            if isinstance(topic, list):
                item = list()
                for tp in topic:
                    item.append(tp.hex())
                topic_hexes.append(item)
            else:
                topic_hexes.append(topic.hex())

        params: list = [{
            "fromBlock": amended_block_nums[0],
            "toBlock": amended_block_nums[1],
            "address": [address.with_checksum() for address in addresses],
            "topics": topic_hexes
        }]
        resp = self.send_request("eth_getLogs", params)
        try:
            return [EthLog.from_dict(log) for log in resp]
        except KeyError:
            raise RpcExceedRequestTime("Node: getLog time out")

    # **************************************** fee data ************************************************
    def eth_get_priority_fee_per_gas(self) -> int:
        resp = self.send_request("eth_maxPriorityFeePerGas", [])
        return int(resp, 16)

    def eth_get_next_base_fee(self) -> Optional[int]:
        block = self.eth_get_latest_block(verbose=False)

        current_base_fee = block.base_fee_per_gas
        if current_base_fee is None:
            return None

        block_gas_limit_half = block.gas_limit // 2
        max_base_fee_change_rate = 0.125
        current_block_gas = block.gas_used

        gas_offset = current_block_gas - block_gas_limit_half
        gas_offset_rate = gas_offset / block_gas_limit_half
        gas_change_rate = gas_offset_rate * max_base_fee_change_rate
        next_base_fee = current_base_fee * (1 + gas_change_rate)
        return int(next_base_fee)

    def eth_get_gas_price(self) -> int:
        resp = self.send_request("eth_gasPrice", [])
        return int(resp, 16)

    # **************************************** basic method ************************************************
    def eth_call(self, call_tx: dict) -> EthHexBytes:
        resp = self.send_request('eth_call', [call_tx, "latest"])
        return EthHexBytes(resp)

    def eth_estimate_gas(self, tx: dict):
        resp = self.send_request("eth_estimateGas", [tx, "latest"])
        return int(resp, 16)

    # matured height 적용하지 않음.
    def eth_get_user_nonce(self, address: EthAddress, height: Union[int, str] = "latest") -> int:
        height_hex_or_latest = _hex_height_or_latest(height)
        if not isinstance(address, EthAddress):
            raise Exception("address type must be \"EthAddress\" type")
        resp = self.send_request("eth_getTransactionCount", [address.hex(), height_hex_or_latest])
        return int(resp, 16)

    def eth_send_raw_transaction(self, signed_serialized_tx: EthHexBytes) -> EthHashBytes:
        resp = self.send_request("eth_sendRawTransaction", [signed_serialized_tx.hex()])
        return EthHashBytes(resp)


class TestTransaction(unittest.TestCase):
    def setUp(self) -> None:
        global_logger.init(log_file_name="test.log")
        self.cli = EthRpcClient.from_config_files(
            "configs/entity.relayer.json",
            "configs/entity.relayer.private.json",
            chain_index=Chain.BFC_MAIN
        )

    def test_rpc_non_result_exception(self):
        self.assertRaises(RpcNoneResult, self.cli.eth_get_block_by_hash, (EthHashBytes("0x" + "00" * 32)))
