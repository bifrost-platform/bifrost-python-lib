import json
import requests
import time
from typing import List, Optional, Union
from json import JSONDecodeError
from requests import Response

from .consts import *
from .exceptions import raise_integrated_exception, RpcOutOfStatusCode, RpCMaxRetry
from .utils import merge_dict, hex_height_or_latest
from ..ethtype.amount import EthAmount
from ..ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes
from ..ethtype.block import EthBlock
from ..ethtype.exceptions import *
from ..ethtype.receipt import EthReceipt, EthLog
from ..ethtype.transaction import EthTransaction
from ...logger import global_logger
from ...prometheus_metric import PrometheusExporter


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
            chain_name: str = DEFAULT_CHAIN_NAME,
            receipt_max_try: int = DEFAULT_RECEIPT_MAX_RETRY,
            block_period_sec: int = DEFAULT_BLOCK_PERIOD_SECS,
            block_aging_period: int = DEFAULT_BLOCK_AGING_BLOCKS,
            rpc_server_downtime_allow_sec: int = DEFAULT_RPC_RESEND_DELAY_SEC,
            transaction_block_delay: int = DEFAULT_RPC_TX_BLOCK_DELAY
    ):
        self.__chain: str = chain_name
        self.__url_with_access_key = url_with_access_key
        self.__receipt_max_try = DEFAULT_RECEIPT_MAX_RETRY if receipt_max_try is None else receipt_max_try
        self.__block_period_sec = DEFAULT_BLOCK_PERIOD_SECS if block_period_sec is None else block_period_sec
        self.__block_aging_period = DEFAULT_BLOCK_AGING_BLOCKS if block_aging_period is None else block_aging_period
        self.__rpc_server_downtime_allow_sec = DEFAULT_RPC_RESEND_DELAY_SEC \
            if rpc_server_downtime_allow_sec is None else rpc_server_downtime_allow_sec
        self.__transaction_block_delay = DEFAULT_RPC_TX_BLOCK_DELAY \
            if transaction_block_delay is None else transaction_block_delay

        # for debug and monitoring
        self.call_num = 0

        # check connection
        self.__chain_id: Optional[int] = None
        if self.__url_with_access_key:
            resp = self.send_request("eth_chainId", [])
            self.__chain_id = int(resp, 16)

    @classmethod
    def from_config_dict(cls, config: dict, private_config: dict = None):
        chain_config = merge_dict(config, private_config)
        chain_name = chain_config.get("chain_name")
        if chain_name is None:
            raise Exception("Chain name is required")

        return cls(
            chain_config["url_with_access_key"],
            chain_name,
            chain_config.get("receipt_max_try"),
            chain_config.get("block_period_sec"),
            chain_config.get("block_aging_period"),
            chain_config.get("rpc_server_downtime_allow_sec")
        )

    @classmethod
    def from_config_files(cls, config_file: str, private_config_file: str = None):
        with open(config_file, "r") as f:
            config = json.load(f)
        if private_config_file is None:
            private_config = None
        else:
            with open(private_config_file, "r") as f:
                private_config = json.load(f)
        return cls.from_config_dict(config, private_config)

    @property
    def url(self) -> str:
        return self.__url_with_access_key

    @url.setter
    def url(self, url: str):
        self.__url_with_access_key = url

    @property
    def block_aging_period(self) -> int:
        return self.__block_aging_period

    @property
    def resend_delay_sec(self) -> int:
        return self.__rpc_server_downtime_allow_sec

    @property
    def tx_commit_time_sec(self) -> int:
        return self.__block_period_sec * (self.__transaction_block_delay + self.__block_aging_period)

    @property
    def chain_name(self) -> str:
        """ return chain index specified from the configuration. """
        return self.__chain

    @property
    def chain_id(self) -> int:
        """ return chain id emitted by the rpc node. """
        return self.__chain_id

    def send_request_base(self, method: str, params: list, cnt: int = 0) -> Response:
        if cnt > RPC_MAX_RESEND_ITER:
            raise RpCMaxRetry(self.chain_name, "Exceeded max re-try cnt")

        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        headers = {'Content-type': 'application/json'}

        PrometheusExporter.exporting_rpc_requested(self.chain_name)
        self.call_num += 1

        response = requests.post(self.url, json=body, headers=headers)
        code = response.status_code
        if code < 200 or 400 < code:
            raise RpcOutOfStatusCode(self.chain_name, "code({}), msg({})".format(code, response.content))

        return response

    def send_request(
            self, method: str, params: list, cnt: int = 0, resend_on_fail: bool = False
    ) -> Optional[Union[dict, str]]:
        while True:
            try:
                cnt += 1
                response = self.send_request_base(method, params, cnt)
                response_json = response.json()
                break
            except RpcOutOfStatusCode or JSONDecodeError as e:
                # export log for out-of-status error
                PrometheusExporter.exporting_rpc_failed(self.chain_name)
                global_logger.formatted_log("RPCException", related_chain=self.__chain, msg=str(e))

                # sleep
                sleep_notify_msg = "re-tried after {} secs".format(self.__rpc_server_downtime_allow_sec)
                global_logger.formatted_log("RPCException", related_chain=self.__chain, msg=sleep_notify_msg)
                time.sleep(self.__rpc_server_downtime_allow_sec)

                # re-send the request
                resend_notify_msg = "re-send rpc request: method({}), params({})".format(method, params)
                global_logger.formatted_log("RPCException", related_chain=self.__chain, msg=resend_notify_msg)

                if not resend_on_fail:
                    raise e

            except RpCMaxRetry:
                raise RpCMaxRetry(self.chain_name, "Exceeded max re-try cnt")

            except Exception as e:
                # raise not handled exception
                raise_integrated_exception(self.chain_name, e)

        if "result" in list(response_json.keys()):
            return response_json["result"]

        # Evm error always gets caught here.
        PrometheusExporter.exporting_rpc_failed(self.chain_name)
        if "error" in list(response_json.keys()):
            raise_integrated_exception(self.chain_name, error_json=response_json["error"])
        else:
            raise Exception("Not handled error on {}: {}".format(self.chain_name, response.content))

    def amend_height_to_matured_height(self, height: Union[int, str]) -> Union[List[str], str]:
        """
        reduce heights whenever each height is bigger than matured height.
        note that matured height means the maximum confirmed block height.
        """
        matured_max_height = self.eth_get_latest_block_number(matured_only=True)
        if height == "latest":
            return hex(matured_max_height)
        elif isinstance(height, int):
            return hex(min(height, matured_max_height))
        elif isinstance(height, str):
            return hex(min(int(height, 16), matured_max_height))
        else:
            raise Exception("Invalid type of height: {}".format(height))

    def eth_get_latest_block_number(self, matured_only: bool = False) -> int:
        """ returns the latest block height. """
        resp = self.send_request("eth_blockNumber", [])
        latest_height = int(resp, 16)
        return latest_height if not matured_only else latest_height - self.__block_aging_period

    def _get_block(self, method: str, params: list, matured_only: bool = False) -> Optional[EthBlock]:
        resp = self.send_request(method, params)
        if resp is None:
            return resp

        block = EthBlock.from_dict(resp)
        if matured_only and block.number >= self.eth_get_latest_block_number(matured_only=True):
            return None

        return block

    def eth_get_latest_block(self, verbose: bool = False, matured_only: bool = False) -> EthBlock:
        latest_height = self.eth_get_latest_block_number(matured_only)
        return self._get_block("eth_getBlockByNumber", [hex(latest_height), verbose])

    def eth_get_block_by_hash(
            self, block_hash: EthHashBytes, verbose: bool = False, matured_only: bool = False
    ) -> Optional[EthBlock]:
        if not isinstance(block_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(block_hash))
        return self._get_block("eth_getBlockByHash", [block_hash.hex(), verbose], matured_only)

    def eth_get_block_by_height(
            self, height: Union[int, str] = "latest", verbose: bool = False, matured_only: bool = False
    ) -> Optional[EthBlock]:
        height_hex_or_latest = hex_height_or_latest(height)
        return self._get_block("eth_getBlockByNumber", [height_hex_or_latest, verbose], matured_only)

    def _get_transaction(self, method: str, params: list, matured_only: bool = False) -> Optional[EthTransaction]:
        resp = self.send_request(method, params)
        if resp is None:
            return None

        fetched_tx: EthTransaction = EthTransaction.from_dict(resp)
        if matured_only and fetched_tx.block_number >= self.eth_get_latest_block_number(matured_only=True):
            return None
        return fetched_tx

    def eth_get_transaction_by_hash(self, tx_hash: EthHashBytes, matured_only: bool = False) -> Optional[EthTransaction]:
        if not isinstance(tx_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(tx_hash))
        return self._get_transaction("eth_getTransactionByHash", [tx_hash.hex()], matured_only)

    def eth_get_transaction_by_height_and_index(self, height: int, tx_index: int, matured_only: bool = False) -> Optional[EthTransaction]:
        if not isinstance(height, int):
            raise EthTypeError(int, type(height))
        if not isinstance(tx_index, int):
            raise EthTypeError(int, type(tx_index))
        return self._get_transaction("eth_getTransactionByBlockNumberAndIndex", [hex(height), hex(tx_index)], matured_only)

    def eth_get_transaction_by_hash_and_index(
            self, block_hash: EthHashBytes, tx_index: int, matured_only: bool = False
    ) -> Optional[EthTransaction]:
        if not isinstance(block_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(block_hash))
        if not isinstance(tx_index, int):
            raise EthTypeError(int, type(tx_index))
        return self._get_transaction("eth_getTransactionByBlockHashAndIndex", [block_hash.hex(), hex(tx_index)], matured_only)

    def _get_receipt(self, tx_hash: EthHashBytes, matured_only: bool = False) -> Optional[EthReceipt]:
        resp = self.send_request('eth_getTransactionReceipt', [tx_hash.hex()])
        if resp is None:
            return None

        fetched_receipt: EthReceipt = EthReceipt.from_dict(resp)
        if matured_only and fetched_receipt.block_number >= self.eth_get_latest_block_number(matured_only=True):
            return None
        return fetched_receipt

    def eth_receipt_without_wait(self, tx_hash: EthHashBytes, matured_only: bool = False) -> Optional[EthReceipt]:
        return self._get_receipt(tx_hash, matured_only)

    def eth_receipt_with_wait(self, tx_hash: EthHashBytes, matured_only: bool = False) -> Optional[EthReceipt]:
        for i in range(self.__receipt_max_try):
            receipt = self._get_receipt(tx_hash, matured_only)
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

        amended_block_nums = [self.amend_height_to_matured_height(height) for height in [from_block, to_block]]

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

    def eth_get_balance(
            self, address: EthAddress, height: Union[int, str] = "latest", matured_only: bool = False
    ) -> EthAmount:
        """ queries matured balance of the user. """
        if not isinstance(address, EthAddress):
            raise Exception("address type must be \"EthAddress\" type")
        if matured_only:
            height = self.amend_height_to_matured_height(height)

        resp = self.send_request("eth_getBalance", [address.hex(), height])
        return EthAmount(resp)

    def eth_get_user_nonce(self, address: EthAddress, height: Union[int, str] = "latest") -> int:
        height_hex_or_latest = hex_height_or_latest(height)
        if not isinstance(address, EthAddress):
            raise Exception("address type must be \"EthAddress\" type")
        resp = self.send_request("eth_getTransactionCount", [address.hex(), height_hex_or_latest])
        return int(resp, 16)

    def eth_send_raw_transaction(self, signed_serialized_tx: EthHexBytes) -> EthHashBytes:
        resp = self.send_request("eth_sendRawTransaction", [signed_serialized_tx.hex()])
        return EthHashBytes(resp)
