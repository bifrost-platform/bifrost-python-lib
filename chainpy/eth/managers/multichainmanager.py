import json
from typing import Optional, List

from .utils import merge_dict
from ..ethtype.account import EthAccount
from ..ethtype.amount import EthAmount
from ..ethtype.contract import EthContract
from ..ethtype.hexbytes import EthHashBytes, EthAddress
from ..ethtype.receipt import EthReceipt
from ..ethtype.transaction import EthTransaction
from ..managers.contracthandler import DetectedEvent
from ..managers.ethchainmanager import EthChainManager


class MultiChainManager:
    def __init__(self, multichain_config: dict):
        entity_config = multichain_config["entity"]
        self._role = entity_config["role"].capitalize()
        self._account_name = entity_config.get("account_name")

        self._active_account = None
        private_key = entity_config.get("secret_hex")
        if private_key is not None and private_key != "":
            self._active_account = EthAccount.from_secret(private_key)

        self._supported_chains = entity_config["supporting_chains"]

        # config for each chain
        self._chain_managers = dict()
        for chain_name in self._supported_chains:
            chain_config = multichain_config[chain_name]
            chain_manager = EthChainManager.from_config_dict(chain_config)
            if private_key is not None and private_key != "":
                chain_manager.set_account(private_key)
            self._chain_managers[chain_name] = chain_manager

        self._multichain_config = multichain_config["multichain_config"]

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
        for chain_name in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_name)
            chain_manager.set_account(private_key)
        self._active_account = EthAccount.from_secret(private_key)

    @property
    def role(self) -> str:
        return self._role

    @role.setter
    def role(self, role: str):
        capitalized_role = role.capitalize()
        if capitalized_role not in ["User", "Fast-relayer", "Slow-relayer", "Relayer"]:
            raise Exception("Invalid role: {}".format(role))
        self._role = capitalized_role

    @property
    def account_name(self) -> Optional[str]:
        return self._account_name

    @property
    def active_account(self) -> Optional[EthAccount]:
        return self._active_account

    @property
    def address(self) -> Optional[EthAddress]:
        return None if self._active_account is None else self._active_account.address

    @property
    def supported_chain_list(self) -> List[str]:
        return list(self._chain_managers.keys())

    @property
    def multichain_config(self) -> dict:
        return self._multichain_config

    def get_chain_manager_of(self, chain_name: str) -> EthChainManager:
        return self._chain_managers.get(chain_name)

    def get_contract_obj_on(self, chain_name: str, contract_name: str) -> Optional[EthContract]:
        return self.get_chain_manager_of(chain_name).get_contract_by_name(contract_name)

    def world_call(self, chain_name: str, contract_name: str, method_name: str, method_params: list):
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.call_transaction(contract_name, method_name, method_params)

    def world_build_transaction(
        self,
        chain_name: str,
        contract_name: str,
        method_name: str,
        method_params: list, value: EthAmount = None
    ) -> EthTransaction:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.build_transaction(contract_name, method_name, method_params, value)

    def world_send_transaction(
        self,
        chain_name: str,
        tx_with_fee: EthTransaction,
        gas_limit_multiplier: float = 1.0
    ) -> EthHashBytes:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.send_transaction(tx_with_fee, gas_limit_multiplier=gas_limit_multiplier)

    def world_receipt_with_wait(
        self, chain_name: str, tx_hash: EthHashBytes
    ) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.eth_receipt_with_wait(tx_hash)

    def try_replace_transaction(self, chain_name: str, tx_hash: EthHashBytes) -> (EthHashBytes, bool):
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.eth_replace_transaction(tx_hash)

    def world_receipt_without_wait(self, chain_name: str, tx_hash: EthHashBytes) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_name)
        return chain_manager.eth_receipt_without_wait(tx_hash)

    def collect_unchecked_multichain_events(self) -> List[DetectedEvent]:
        unchecked_events = list()
        for chain_name in self._supported_chains:
            chain_manager = self.get_chain_manager_of(chain_name)
            unchecked_events += chain_manager.collect_unchecked_single_chain_events()
        return unchecked_events

    def decode_event(self, detected_event: DetectedEvent) -> tuple:
        contract_obj = self.get_contract_obj_on(detected_event.chain_name, detected_event.contract_name)
        return contract_obj.decode_event(detected_event.event_name, detected_event.data)
