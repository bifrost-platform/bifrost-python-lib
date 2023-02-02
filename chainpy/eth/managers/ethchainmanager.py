import threading
import unittest
from typing import Optional, Union, List

from .exceptions import raise_integrated_exception
from .rpchandler import DEFAULT_RECEIPT_MAX_RETRY, DEFAULT_BLOCK_PERIOD_SECS, DEFAULT_BLOCK_AGING_BLOCKS, \
    DEFAULT_RPC_DOWN_ALLOW_SECS, DEFAULT_RPC_TX_BLOCK_DELAY
from bridgeconst.consts import Chain
from ..ethtype.hexbytes import EthHashBytes, EthAddress, EthHexBytes
from ..ethtype.amount import EthAmount
from ..ethtype.account import EthAccount
from ..ethtype.transaction import EthTransaction
from ..managers.utils import FeeConfig, merge_dict
from ..managers.contracthandler import EthContractHandler

PRIORITY_FEE_MULTIPLIER = 4
TYPE0_GAS_MULTIPLIER = 1.5
TYPE2_GAS_MULTIPLIER = 2


class EthChainManager(EthContractHandler):
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
            latest_height: int = 0,
            max_log_num: int = 1000,

            fee_config: dict = None
    ):
        super().__init__(
            url_with_access_key,
            contracts,
            chain_index,
            abi_dir,
            receipt_max_try,
            block_period_sec,
            block_aging_period,
            rpc_server_downtime_allow_sec,
            transaction_commit_multiplier,
            events,
            latest_height,
            max_log_num
        )

        # self.__chain_index = chain_index
        self.__account = EthAccount.from_secret("0xbfc")
        self.__nonce = 0
        self.__nonce_lock = threading.Lock()

        if fee_config is None:
            self.__fee_config = FeeConfig.from_dict({"type": 0, "gas_price": 2 ** 255 - 1})
        else:
            self.__fee_config = FeeConfig.from_dict(fee_config)

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
            merged_config.get("transaction_commit_multiplier"),

            merged_config.get("events"),
            merged_config.get("bootstrap_latest_height"),
            merged_config.get("max_log_num"),

            merged_config.get("fee_config")
        )

    @property
    def account(self) -> Optional[EthAccount]:
        return self.__account

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
            method_params: list) -> EthHexBytes:
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
            value: EthAmount = None) -> EthTransaction:
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
            # TODO bifrost specific config
            if self.chain_index == Chain.BFC_TEST or self.chain_index == Chain.BFC_MAIN:
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

    def send_transaction(self,
                         transaction: EthTransaction,
                         gas_limit: int = None,
                         boost: bool = False,
                         gas_limit_multiplier: float = 1.0) -> EthHashBytes:
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

        tx_hash = None
        if is_sendable:
            tx_with_fee.set_nonce(self.issue_nonce)

            if not tx_with_fee.is_sendable():
                raise Exception("Check transaction parameters")
            signed_raw_tx = tx_with_fee.sign_transaction(self.__account)
            try:
                tx_hash = self.eth_send_raw_transaction(signed_raw_tx)
                if tx_hash is None:
                    tx_hash = EthHashBytes.default()
            except Exception as e:
                raise_integrated_exception(e)
        else:
            tx_hash = EthHashBytes.default()

        return tx_hash

    def transfer_native_coin(self,
                             receiver: EthAddress,
                             value: EthAmount,
                             boost: bool = False) -> EthHashBytes:
        if self.__account is None:
            raise Exception("No Account")
        raw_tx = EthTransaction.init(self.chain_id, receiver, value, EthHexBytes.default())
        return self.send_transaction(raw_tx, boost=boost)

    def native_balance(self, addr: EthAddress = None) -> EthAmount:
        if self.__account is None and addr is None:
            raise Exception("No Account")

        if addr is None:
            addr = self.account.address
        return self.eth_get_balance(addr)


class TestTransaction(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = EthChainManager.from_config_files(
            "../configs/entity.relayer.json",
            "../configs/entity.relayer.private.json",
            chain_index=Chain.BFC_TEST
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
            data=EthHexBytes(
                "0x6196d920000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000001524d2eadae57a7f06f100476a57724c1295c8fe99db52b6af3e3902cc8210e97000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000b99000000000000000000000000000000000000000000000000000000000000000001000000000000000000062bf8e916ee7d6d68632b2ee0d6823a5c9a7cd69c874e")
        )
        tx_obj.set_nonce(int("0x301f", 16)).set_gas_prices(int("0x015d3ef79801", 16), int("0x01", 16)).set_gas_limit(
            int("0x036e54", 16))
        self.assertEqual(tx_obj.serialize(), self.serialized_tx)

    def test_account(self):
        account = EthAccount.from_secret("0xbfc")
