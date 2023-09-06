import threading
from typing import Optional, Union, List

from .rpchandler import (
    DEFAULT_RECEIPT_MAX_RETRY,
    DEFAULT_BLOCK_PERIOD_SECS,
    DEFAULT_BLOCK_AGING_BLOCKS,
    DEFAULT_RPC_RESEND_DELAY_SEC,
    DEFAULT_RPC_TX_BLOCK_DELAY
)
from ..ethtype.account import EthAccount
from ..ethtype.amount import EthAmount
from ..ethtype.hexbytes import EthHashBytes, EthAddress, EthHexBytes
from ..ethtype.transaction import EthTransaction
from ..managers.contracthandler import EthContractHandler
from ..managers.utils import FeeConfig, merge_dict

PRIORITY_FEE_MULTIPLIER = 4
TYPE0_GAS_MULTIPLIER = 1.5
TYPE2_GAS_MULTIPLIER = 2


class EthChainManager(EthContractHandler):
    def __init__(
        self,
        url_with_access_key: str,
        contracts: List[dict],
        chain_name: str,
        abi_dir: str = None,
        receipt_max_try: int = DEFAULT_RECEIPT_MAX_RETRY,
        block_period_sec: int = DEFAULT_BLOCK_PERIOD_SECS,
        block_aging_period: int = DEFAULT_BLOCK_AGING_BLOCKS,
        rpc_server_downtime_allow_sec: int = DEFAULT_RPC_RESEND_DELAY_SEC,
        transaction_block_delay: int = DEFAULT_RPC_TX_BLOCK_DELAY,

        events: List[dict] = None,
        latest_height: int = 0,
        max_log_num: int = 1000,

        fee_config: dict = None
    ):
        super().__init__(
            url_with_access_key,
            contracts,
            chain_name,
            abi_dir,
            receipt_max_try,
            block_period_sec,
            block_aging_period,
            rpc_server_downtime_allow_sec,
            transaction_block_delay,
            events,
            latest_height,
            max_log_num
        )

        self.__account = EthAccount.from_secret("0xbfc")
        self.__nonce = 0
        self.__nonce_lock = threading.Lock()

        if fee_config is None:
            self.__fee_config = FeeConfig.from_dict({"type": 0, "gas_price": 2 ** 255 - 1})
        else:
            self.__fee_config = FeeConfig.from_dict(fee_config)

    @classmethod
    def from_config_dict(cls, config: dict, private_config: dict = None):
        chain_config = merge_dict(config, private_config)
        chain_name = chain_config.get("chain_name")
        if chain_config is None:
            raise Exception("Chain name is required")

        contracts = chain_config.get("contracts")
        if contracts is None:
            contracts = []

        return cls(
            chain_config["url_with_access_key"],
            contracts,
            chain_name,
            chain_config.get("abi_dir"),
            chain_config.get("receipt_max_try"),
            chain_config.get("block_period_sec"),
            chain_config.get("block_aging_period"),
            chain_config.get("rpc_server_downtime_allow_sec"),
            chain_config.get("transaction_block_delay"),

            chain_config.get("events"),
            chain_config.get("bootstrap_latest_height"),
            chain_config.get("max_log_num"),

            chain_config.get("fee_config")
        )

    @property
    def account(self) -> Optional[EthAccount]:
        return self.__account

    @property
    def address(self) -> Optional[EthAddress]:
        return None if self.__account is None else self.__account.address

    def set_account(self, private_key: str):
        self.__account = EthAccount.from_secret(private_key)
        self.__nonce = self.eth_get_user_nonce(self.__account.address)

    @property
    def issue_nonce(self) -> Optional[int]:
        if self.__nonce is not None:
            self.__nonce_lock.acquire()
            nonce = self.__nonce
            self.__nonce += 1
            self.__nonce_lock.release()
            return nonce
        else:
            return None

    @property
    def fee_config(self) -> FeeConfig:
        """
        The fee parameters read from the config file.
        This is used as the upper limit of fe when transaction is transmitted.
        """
        return self.__fee_config

    @property
    def tx_type(self) -> int:
        """ Type of transaction to be sent by tx-handler -1, 0, 1 and 2"""
        return self.__fee_config.type

    def _encode_transaction_data(
        self,
        contract_name: str,
        method_name: str,
        method_params: list
    ) -> EthHexBytes:
        contract = self.get_contract_by_name(contract_name)
        data = contract.abi.get_method(method_name).encode_input_data(method_params)
        return data

    def estimate_tx(self, transaction: EthTransaction, from_addr: EthAddress = None) -> int:
        """ estimate the transaction and return its gas limit"""
        tx_dict = transaction.call_dict()
        if from_addr is not None:
            tx_dict["from"] = from_addr.with_checksum()

        if "chainId" in tx_dict:
            del tx_dict["chainId"]

        return self.eth_estimate_gas(tx_dict)

    def call_transaction(
        self,
        contract_name: str,
        method_name: str,
        method_params: list,
        sender_addr: EthAddress = None,
        value: EthAmount = None) -> Union[EthHexBytes, tuple]:
        data = self._encode_transaction_data(contract_name, method_name, method_params)
        contract_address = self.get_contract_by_name(contract_name).address

        if sender_addr is None:
            sender_addr = self.__account.address

        call_tx = EthTransaction.init(self.chain_id, contract_address, value, data, sender_addr)

        result = self.eth_call(call_tx.call_dict())
        contract = self.get_contract_by_name(contract_name)
        return contract.abi.get_method(method_name).decode_output_data(result)

    def build_transaction(
        self,
        contract_name: str,
        method_name: str,
        method_params: list,
        value: EthAmount = None
    ) -> EthTransaction:
        data = self._encode_transaction_data(contract_name, method_name, method_params)
        contract_address = self.get_contract_by_name(contract_name).address
        value = EthAmount.zero() if value is None else value

        return EthTransaction.init(self.chain_id, contract_address, value, data)

    def fetch_network_fee_parameters(self) -> (Optional[int], Optional[int], Optional[int]):
        """ fetch fee parameters from the network """
        gas_price, base_fee_price, priority_fee_price = None, None, None
        if self.tx_type == 0:
            gas_price = self.eth_get_gas_price()
        elif self.tx_type == 2:
            priority_fee_price = self.eth_get_priority_fee_per_gas()
            base_fee_price = self.eth_get_next_base_fee()

            # bifrost specific config
            if self.chain_name.split("_")[0] == "BFC":
                base_fee_price = max(base_fee_price, 1000 * 10 ** 9)
        else:
            raise Exception("Not supported fee type")
        return gas_price, base_fee_price, priority_fee_price

    def set_gas_limit_and_fee(
        self,
        tx: EthTransaction,
        gas_limit: int = None,
        gas_limit_multiplier: float = 1.0,
        boost: bool = False,
        sender_account: EthAccount = None,
    ) -> (bool, EthTransaction):

        if gas_limit is None:
            gas_limit = self.estimate_tx(tx, sender_account.address)
        tx.set_gas_limit(int(gas_limit * gas_limit_multiplier))

        # fetch fee from network
        net_gas_price, net_base_fee_price, net_priority_fee_price = self.fetch_network_fee_parameters()

        if self.tx_type < 2:
            net_gas_price = int(net_gas_price * TYPE0_GAS_MULTIPLIER)
            if boost:
                net_gas_price = int(net_gas_price * 2.0)
            is_sendable = False if net_gas_price > self.fee_config.gas_price else True
            tx.set_gas_price(net_gas_price)
        else:
            net_priority_fee_price = int((net_priority_fee_price + 1) * PRIORITY_FEE_MULTIPLIER)
            if boost:
                net_base_fee_price = int(net_base_fee_price * 1.1)
                net_priority_fee_price = int(net_priority_fee_price * 1.1)
            net_max_gas_price = int((net_priority_fee_price + net_base_fee_price) * TYPE0_GAS_MULTIPLIER)

            is_sendable1 = True if net_priority_fee_price < self.fee_config.max_priority_price else False
            is_sendable2 = True if net_max_gas_price < self.fee_config.max_gas_price else False
            is_sendable = bool(is_sendable1 * is_sendable2)
            tx.set_gas_prices(net_max_gas_price, net_priority_fee_price)

        return is_sendable, tx

    def send_transaction(
        self,
        transaction: EthTransaction,
        gas_limit: int = None,
        boost: bool = False,
        gas_limit_multiplier: float = 1.0
    ) -> EthHashBytes:
        if self.__account is None:
            raise Exception("No account")

        # estimate tx and setting gas parameter
        is_sendable, tx_with_fee = self.set_gas_limit_and_fee(
            transaction,
            gas_limit=gas_limit,
            boost=boost,
            gas_limit_multiplier=gas_limit_multiplier,
            sender_account=self.__account
        )

        if is_sendable:
            tx_with_fee.set_nonce(self.issue_nonce)

            if not tx_with_fee.is_sendable():
                raise Exception("Check transaction parameters")
            signed_raw_tx = tx_with_fee.sign_transaction(self.__account)
            tx_hash = self.eth_send_raw_transaction(signed_raw_tx)
            if tx_hash is None:
                tx_hash = EthHashBytes.default()
        else:
            tx_hash = EthHashBytes.default()

        return tx_hash

    def transfer_native_coin(
        self,
        receiver: EthAddress,
        value: EthAmount,
        boost: bool = False
    ) -> EthHashBytes:
        if self.__account is None:
            raise Exception("No Account")
        raw_tx = EthTransaction.init(self.chain_id, receiver, value, EthHexBytes.default())
        return self.send_transaction(raw_tx, boost=boost)

    def native_balance(self, addr: EthAddress = None) -> EthAmount:
        if self.__account is None and addr is None:
            raise Exception("No Account")

        if addr is None:
            addr = self.address
        return self.eth_get_balance(addr)
