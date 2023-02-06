import json
import unittest
from typing import Optional, List, Dict

from .utils import merge_dict
from ..ethtype.account import EthAccount
from ..ethtype.amount import EthAmount
from ..ethtype.chaindata import EthReceipt
from bridgeconst.consts import Chain, Asset
from ..ethtype.contract import EthContract
from ..ethtype.hexbytes import EthHashBytes, EthAddress, EthHexBytes
from ..ethtype.transaction import EthTransaction
from ..managers.contracthandler import DetectedEvent
from ..managers.ethchainmanager import EthChainManager


class MultiChainManager:
    def __init__(self, multichain_config: dict):
        entity_config = multichain_config["entity"]
        self.__role = entity_config["role"].capitalize()
        self.__account_name = entity_config.get("account_name")

        private_key = entity_config.get("secret_hex")
        if private_key is not None and private_key != "":
            self.__active_account = EthAccount.from_secret(private_key)
        self.__supported_chains = [Chain[chain_name] for chain_name in entity_config["supporting_chains"]]

        # config for each chain
        self.__chain_managers = dict()
        for chain_index in self.__supported_chains:
            chain_config = multichain_config[chain_index.name.upper()]
            chain_manager = EthChainManager.from_config_dict(chain_config, chain_index=chain_index)
            if private_key is not None and private_key != "":
                chain_manager.set_account(private_key)
            self.__chain_managers[chain_index] = chain_manager

        self.__multichain_config = multichain_config["multichain_config"]

    @classmethod
    def from_configs(cls, config: dict, private_config: dict):
        merged_config = merge_dict(config, private_config)
        return cls(merged_config)

    @classmethod
    def from_config_files(cls, config_file: str, private_config_file: str = None):
        with open(config_file, "r") as f:
            config = json.load(f)
        if private_config_file is None:
            private_config = None
        else:
            with open(private_config_file, "r") as f:
                private_config = json.load(f)
        return cls.from_configs(config, private_config)

    def set_account(self, private_key: str):
        for chain_index in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_index)
            chain_manager.set_account(private_key)
        self.__active_account = EthAccount.from_secret(private_key)

    @property
    def role(self) -> str:
        return self.__role

    @role.setter
    def role(self, role: str):
        capitalized_role = role.capitalize()
        if capitalized_role not in ["User", "Fast-relayer", "Slow-relayer", "Relayer"]:
            raise Exception("Invalid role: {}".format(role))
        self.__role = capitalized_role

    @property
    def account_name(self) -> Optional[str]:
        return self.__account_name

    @property
    def active_account(self) -> EthAccount:
        return self.__active_account

    @property
    def supported_chain_list(self) -> list:
        return list(self.__chain_managers.keys())

    @property
    def multichain_config(self) -> dict:
        return self.__multichain_config

    def get_chain_manager_of(self, chain_index: Chain) -> EthChainManager:
        return self.__chain_managers.get(chain_index)

    def get_contract_obj_on(self, chain_index: Chain, contract_name: str) -> Optional[EthContract]:
        return self.get_chain_manager_of(chain_index).get_contract_by_name(contract_name)

    def world_call(self, chain_index: Chain, contract_name: str, method_name: str, method_params: list):
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.call_transaction(contract_name, method_name, method_params)

    def world_build_transaction(self,
                                chain_index: Chain,
                                contract_name: str,
                                method_name: str,
                                method_params: list, value: EthAmount = None) -> EthTransaction:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.build_transaction(contract_name, method_name, method_params, value)

    def world_send_transaction(self,
                               chain_index: Chain,
                               tx_with_fee: EthTransaction,
                               gas_limit_multiplier: float = 1.0) -> EthHashBytes:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.send_transaction(tx_with_fee, gas_limit_multiplier=gas_limit_multiplier)

    def world_receipt_with_wait(
            self, chain_index: Chain, tx_hash: EthHashBytes, matured: bool = True) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.eth_receipt_with_wait(tx_hash, matured)

    def world_receipt_without_wait(self, chain_index: Chain, tx_hash: EthHashBytes) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.eth_receipt_without_wait(tx_hash)

    def collect_unchecked_multichain_event_in_range(self, event_name: str, _range: Dict[Chain, List[int]]):
        unchecked_events = list()
        for chain_index in self.__supported_chains:
            chain_manager = self.get_chain_manager_of(chain_index)
            from_block, to_block = _range[chain_index][0], _range[chain_index][1]
            unchecked_events += chain_manager.ranged_collect_events(event_name, from_block, to_block)
        return unchecked_events

    def collect_unchecked_multichain_events(self) -> List[DetectedEvent]:
        unchecked_events = list()
        for chain_index in self.__supported_chains:
            chain_manager = self.get_chain_manager_of(chain_index)
            unchecked_events += chain_manager.collect_unchecked_single_chain_events()
        return unchecked_events

    def decode_event(self, detected_event: DetectedEvent) -> tuple:
        contract_obj = self.get_contract_obj_on(detected_event.chain_index, detected_event.contract_name)
        return contract_obj.decode_event(detected_event.event_name, detected_event.data)

    def world_transfer_coin(
            self, chain_index: Chain, to_addr: EthAddress, value: EthAmount) -> EthHashBytes:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.transfer_native_coin(to_addr, value)

    def world_balance(self, chain: Chain, asset: Asset = None, user_addr: EthAddress = None) -> EthAmount:
        chain_manager = self.get_chain_manager_of(chain)
        addr = user_addr if user_addr is not None else self.active_account.address
        if asset is None or asset.is_coin():
            return chain_manager.native_balance(user_addr)
        else:
            result = chain_manager.call_transaction(asset.name, "balanceOf", [addr.with_checksum()])[0]
            return EthAmount(result, asset.decimal)


class TestTransaction(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = MultiChainManager.from_config_files(
            "../configs/entity.relayer.json",
            "../configs/entity.relayer.private.json"
        )
        self.target_tx_hash = EthHashBytes(0xfb6ceb412ae267643d45b28516565b1ab07f4d16ade200d7e432be892add1448)
        self.serialized_tx = "0xf90153f9015082bfc082301f0186015d3ef7980183036e54947abd332cf88ca31725fffb21795f90583744535280b901246196d920000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000001524d2eadae57a7f06f100476a57724c1295c8fe99db52b6af3e3902cc8210e97000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000b99000000000000000000000000000000000000000000000000000000000000000001000000000000000000062bf8e916ee7d6d68632b2ee0d6823a5c9a7cd69c874ec0 "

    def test_serialize_tx_from_rpc(self):
        tx = self.cli.get_chain_manager_of(Chain.BFC_TEST).eth_get_transaction_by_hash(self.target_tx_hash)
        self.assertEqual(tx.serialize(), self.serialized_tx)

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
