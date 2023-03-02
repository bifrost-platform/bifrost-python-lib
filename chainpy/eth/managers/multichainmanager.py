import json
from typing import Optional, List

from bridgeconst.consts import Asset
from .utils import merge_dict
from ..ethtype.account import EthAccount
from ..ethtype.amount import EthAmount
from ..ethtype.receipt import EthReceipt
from ..ethtype.contract import EthContract
from ..ethtype.hexbytes import EthHashBytes, EthAddress
from ..ethtype.transaction import EthTransaction
from ..managers.contracthandler import DetectedEvent
from ..managers.ethchainmanager import EthChainManager


class MultiChainManager:
    def __init__(self, multichain_config: dict):
        entity_config = multichain_config["entity"]
        self.__role = entity_config["role"].capitalize()
        self.__account_name = entity_config.get("account_name")

        self.__active_account = None
        private_key = entity_config.get("secret_hex")
        if private_key is not None and private_key != "":
            self.__active_account = EthAccount.from_secret(private_key)

        self.__supported_chains = entity_config["supporting_chains"]

        # config for each chain
        self.__chain_managers = dict()
        for chain_name in self.__supported_chains:
            chain_config = multichain_config[chain_name]
            chain_manager = EthChainManager.from_config_dict(chain_config)
            if private_key is not None and private_key != "":
                chain_manager.set_account(private_key)
            self.__chain_managers[chain_name] = chain_manager

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
    def active_account(self) -> Optional[EthAccount]:
        return self.__active_account

    @property
    def address(self) -> Optional[EthAddress]:
        return None if self.__active_account is None else self.__active_account.address

    @property
    def supported_chain_list(self) -> list:
        return list(self.__chain_managers.keys())

    @property
    def multichain_config(self) -> dict:
        return self.__multichain_config

    def get_chain_manager_of(self, chain_name: str) -> EthChainManager:
        return self.__chain_managers.get(chain_name)

    def get_contract_obj_on(self, chain_name: str, contract_name: str) -> Optional[EthContract]:
        return self.get_chain_manager_of(chain_name).get_contract_by_name(contract_name)

    def world_call(self, chain_name: str, contract_name: str, method_name: str, method_params: list):
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.call_transaction(contract_name, method_name, method_params)

    def world_build_transaction(self,
                                chain_name: str,
                                contract_name: str,
                                method_name: str,
                                method_params: list, value: EthAmount = None) -> EthTransaction:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.build_transaction(contract_name, method_name, method_params, value)

    def world_send_transaction(self,
                               chain_name: str,
                               tx_with_fee: EthTransaction,
                               gas_limit_multiplier: float = 1.0) -> EthHashBytes:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.send_transaction(tx_with_fee, gas_limit_multiplier=gas_limit_multiplier)

    def world_receipt_with_wait(
            self, chain_name: str, tx_hash: EthHashBytes, matured: bool = True) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.eth_receipt_with_wait(tx_hash, matured)

    def world_receipt_without_wait(self, chain_name: str, tx_hash: EthHashBytes) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.eth_receipt_without_wait(tx_hash)

    def collect_unchecked_multichain_events(self) -> List[DetectedEvent]:
        unchecked_events = list()
        for chain_index in self.__supported_chains:
            chain_manager = self.get_chain_manager_of(chain_index)
            unchecked_events += chain_manager.collect_unchecked_single_chain_events()
        return unchecked_events

    def decode_event(self, detected_event: DetectedEvent) -> tuple:
        contract_obj = self.get_contract_obj_on(detected_event.chain_name, detected_event.contract_name)
        return contract_obj.decode_event(detected_event.event_name, detected_event.data)

    def world_transfer_coin(
            self, chain_name: str, to_addr: EthAddress, value: EthAmount) -> EthHashBytes:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.transfer_native_coin(to_addr, value)

    def world_balance(self, chain_name: str, asset: Asset = None, user_addr: EthAddress = None) -> EthAmount:
        chain_manager = self.get_chain_manager_of(chain_name)
        addr = user_addr if user_addr is not None else self.address
        if asset is None or asset.is_coin():
            return chain_manager.native_balance(user_addr)
        else:
            result = chain_manager.call_transaction(asset.name, "balanceOf", [addr.with_checksum()])[0]
            return EthAmount(result, asset.decimal)
