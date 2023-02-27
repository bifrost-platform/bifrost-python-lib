import copy
from typing import Any
from jsonpath_ng import parse, Fields
from bridgeconst.consts import Chain, Asset


class KeyRequired(Exception):
    def __init__(self, json_expr: Fields):
        msg = " is required"
        super().__init__(str(json_expr) + msg)


class NotMeaningful(Exception):
    def __init__(self, json_expr: Fields, value: Any):
        msg = " should be meaningful, but value()".format(value)
        super().__init__(str(json_expr) + msg)


class NotAllowDefault(Exception):
    def __init__(self, json_expr: Fields, value: Any):
        msg = " is not allowed default value: {}".format(value)
        super().__init__(str(json_expr) + msg)


class TypeNotMatch(Exception):
    def __init__(self, json_expr: Fields, expected_type: type, actual_type: type):
        msg = " expected type ({}), but actual type ({})".format(expected_type, actual_type)
        super().__init__(str(json_expr) + msg)


class InvalidEnum(Exception):
    def __init__(self, json_expr: Fields, expected_enum: type, value: Any):
        msg = " Invalid enum: enum_type({}), value({})".format(expected_enum.__name__, value)
        super().__init__(str(json_expr) + msg)


class NotUsedConfigExist(Exception):
    def __init__(self, json_expr: Fields, data: Any):
        super().__init__(str(json_expr) + " ".format(data))


def is_default(value) -> bool:
    return value == type(value)()


def is_none(value) -> bool:
    return value is None


def is_meaningful(value) -> bool:
    if isinstance(value, list):
        for data in value:
            if is_meaningful(data):
                continue
            return False
        return True
    else:
        return False if is_none(value) else False if is_default(value) else True


class ConfigSanityChecker:
    def __init__(self, config: dict):
        self.config = copy.deepcopy(config)

        supporting_expr = parse("entity.supporting_chains")
        matches = supporting_expr.find(self.config)
        if len(matches) == 0:
            raise Exception("entity.supporting_chains is empty")
        self.supporting_chain_names = copy.deepcopy(matches[0].value)

    def check_valid_type(
            self,
            json_expr: Fields,
            expected_value_type: type,
            is_enum: bool = False,
            key_required: bool = False,
            value_default_allow: bool = True
    ):
        matched_values = [match.value for match in json_expr.find(self.config)]
        if key_required and not matched_values:
            raise KeyRequired(json_expr)

        for value in matched_values:
            if not value_default_allow and is_default(value):
                raise NotAllowDefault(json_expr, value)

            if is_enum:
                try:
                    _enum = expected_value_type[value]
                except KeyError as e:
                    raise InvalidEnum(json_expr, expected_value_type, value)
            else:
                if not isinstance(value, expected_value_type):
                    raise TypeNotMatch(json_expr, expected_value_type, type(value))

    def delete_key_safe(self, json_expr: Fields):
        return json_expr.filter(lambda d: True, self.config)

    def raise_exception_if_not_empty(self, json_expr: Fields):
        value = json_expr.find(self.config)[0].value
        if is_meaningful(value):
            raise NotUsedConfigExist(json_expr, value)

        self.delete_key_safe(json_expr)

    def check_multichain_config(self):
        multichain_expr = parse("multichain_config")
        self.check_valid_type(multichain_expr, dict, key_required=True, value_default_allow=False)

        multichain_period_expr = parse("multichain_config.chain_monitor_period_sec")
        self.check_valid_type(multichain_period_expr, int, key_required=True, value_default_allow=False)
        self.delete_key_safe(multichain_period_expr)

        self.raise_exception_if_not_empty(multichain_expr)

    def check_entity_config(self):
        entity_expr = parse("entity")
        self.check_valid_type(entity_expr, dict, key_required=True, value_default_allow=False)

        supporting_chains_expr = parse("entity.supporting_chains")

        self.check_valid_type(supporting_chains_expr, list, key_required=True, value_default_allow=False)
        supporting_chains_element_expr = parse("entity.supporting_chains[*]")
        self.check_valid_type(supporting_chains_element_expr, Chain, is_enum=True, key_required=True)
        self.delete_key_safe(supporting_chains_element_expr)

        self.delete_key_safe(supporting_chains_expr)

        account_name_expr = parse("entity.account_name")
        is_slow_relayer = account_name_expr.find(self.config)[0].value.lower() == "slow-relayer"
        self.check_valid_type(account_name_expr, str, key_required=False, value_default_allow=True)
        self.delete_key_safe(account_name_expr)

        role_expr = parse("entity.role")
        self.check_valid_type(role_expr, str, key_required=False, value_default_allow=True)
        self.delete_key_safe(role_expr)

        delay_sec_expr = parse("entity.slow_relayer_delay_sec")
        self.check_valid_type(
            delay_sec_expr, int, key_required=is_slow_relayer, value_default_allow=(not is_slow_relayer)
        )
        self.delete_key_safe(delay_sec_expr)

        secret_hex_expr = parse("entity.secret_hex")
        self.check_valid_type(secret_hex_expr, str, key_required=False, value_default_allow=True)
        self.delete_key_safe(secret_hex_expr)

        self.raise_exception_if_not_empty(entity_expr)

    def check_chain_config(self, chain_name: str):
        chain_name_expr = parse("{}.chain_name".format(chain_name))
        self.check_valid_type(chain_name_expr, str, key_required=True, value_default_allow=False)
        self.delete_key_safe(chain_name_expr)

        block_period_sec_expr = parse("{}.block_period_sec".format(chain_name))
        self.check_valid_type(block_period_sec_expr, int, key_required=False, value_default_allow=False)
        self.delete_key_safe(block_period_sec_expr)

        endpoint_expr = parse("{}.url_with_access_key".format(chain_name))
        self.check_valid_type(endpoint_expr, str, key_required=True, value_default_allow=False)
        self.delete_key_safe(endpoint_expr)

        latest_height_expr = parse("{}.bootstrap_latest_height".format(chain_name))
        self.check_valid_type(latest_height_expr, int, key_required=False, value_default_allow=True)
        self.delete_key_safe(latest_height_expr)

        aging_period_expr = parse("{}.block_aging_period".format(chain_name))
        self.check_valid_type(aging_period_expr, int, key_required=False, value_default_allow=False)
        self.delete_key_safe(aging_period_expr)

        tx_delay_expr = parse("{}.transaction_block_delay".format(chain_name))
        self.check_valid_type(tx_delay_expr, int, key_required=False, value_default_allow=False)
        self.delete_key_safe(tx_delay_expr)

        receipt_max_try_expr = parse("{}.receipt_max_try".format(chain_name))
        self.check_valid_type(receipt_max_try_expr, int, key_required=False, value_default_allow=False)
        self.delete_key_safe(receipt_max_try_expr)

        max_log_expr = parse("{}.max_log_num".format(chain_name))
        self.check_valid_type(max_log_expr, int, key_required=False, value_default_allow=False)
        self.delete_key_safe(max_log_expr)

        server_down_time_expr = parse("{}.rpc_server_downtime_allow_sec".format(chain_name))
        self.check_valid_type(server_down_time_expr, int, key_required=False, value_default_allow=False)
        self.delete_key_safe(server_down_time_expr)

        fee_config_expr = parse("{}.fee_config".format(chain_name))
        self.check_valid_type(fee_config_expr, dict, key_required=False, value_default_allow=False)
        fee_config = self.config[chain_name].get("fee_config")
        if fee_config:
            fee_type_expr = parse("{}.fee_config.type".format(chain_name))
            self.check_valid_type(fee_type_expr, int, key_required=True, value_default_allow=True)
            fee_type = fee_config["type"]
            if fee_type not in [0, 1, 2]:
                raise Exception(str(fee_config_expr) + " type must be 0, 1 or 2, actual({})".format(fee_type))
            self.delete_key_safe(fee_type_expr)

            type0_gas_price_expr = parse("{}.fee_config.gas_price".format(chain_name))
            key_required = True if fee_type in [0, 1] else False
            self.check_valid_type(type0_gas_price_expr, int, key_required=key_required, value_default_allow=False)
            self.delete_key_safe(type0_gas_price_expr)

            type2_max_gas_price_expr = parse("{}.fee_config.max_gas_price".format(chain_name))
            key_required = True if not key_required else False
            self.check_valid_type(type2_max_gas_price_expr, int, key_required=key_required, value_default_allow=False)
            self.delete_key_safe(type2_max_gas_price_expr)

            type2_max_priority_price_expr = parse("{}.fee_config.max_priority_price".format(chain_name))
            self.check_valid_type(type2_max_priority_price_expr, int, key_required=key_required, value_default_allow=False)
            self.delete_key_safe(type2_max_priority_price_expr)

            self.raise_exception_if_not_empty(fee_config_expr)

        abi_dir_expr = parse("{}.abi_dir".format(chain_name))
        self.check_valid_type(abi_dir_expr, str, key_required=False, value_default_allow=True)
        self.delete_key_safe(abi_dir_expr)

        contracts_expr = parse("{}.contracts".format(chain_name))
        self.check_valid_type(contracts_expr, list, key_required=False, value_default_allow=True)
        if self.config[chain_name].get("contracts"):
            contracts_names_expr = parse("{}.contracts[*].name".format(chain_name))
            self.check_valid_type(contracts_names_expr, str, key_required=True, value_default_allow=False)
            self.delete_key_safe(contracts_names_expr)

            contracts_addrs_expr = parse("{}.contracts[*].address".format(chain_name))
            self.check_valid_type(contracts_addrs_expr, str, key_required=True, value_default_allow=False)
            self.delete_key_safe(contracts_addrs_expr)

            abi_files_expr = parse("{}.contracts[*].abi_file".format(chain_name))
            self.check_valid_type(abi_files_expr, str, key_required=True, value_default_allow=False)
            self.delete_key_safe(abi_files_expr)

            deploy_height_expr = parse("{}.contracts[*].deploy_height".format(chain_name))
            self.check_valid_type(deploy_height_expr, int, key_required=False, value_default_allow=False)
            self.delete_key_safe(deploy_height_expr)

            self.raise_exception_if_not_empty(contracts_expr)
        self.delete_key_safe(contracts_expr)

        events_expr = parse("{}.events".format(chain_name))
        self.check_valid_type(events_expr, list, key_required=False, value_default_allow=True)
        if self.config[chain_name].get("events"):
            contract_name_expr = parse("{}.events[*].contract_name".format(chain_name))
            self.check_valid_type(contract_name_expr, str, key_required=True, value_default_allow=False)
            self.delete_key_safe(contract_name_expr)

            event_name_expr = parse("{}.events[*].event_name".format(chain_name))
            self.check_valid_type(event_name_expr, str, key_required=True, value_default_allow=False)
            self.delete_key_safe(event_name_expr)

            self.raise_exception_if_not_empty(events_expr)
        self.delete_key_safe(events_expr)

        self.raise_exception_if_not_empty(parse("{}".format(chain_name)))

    def check_oracle_config(self):
        oracle_expr = parse("oracle_config")
        self.check_valid_type(oracle_expr, dict, key_required=False, value_default_allow=True)

        btc_hash_expr = parse("oracle_config.bitcoin_block_hash")
        self.check_valid_type(btc_hash_expr, dict, key_required=True, value_default_allow=False)
        if self.config["oracle_config"].get("bitcoin_block_hash"):
            hash_name_expr = parse("oracle_config.bitcoin_block_hash.name")
            self.check_valid_type(hash_name_expr, str, key_required=True, value_default_allow=False)
            self.delete_key_safe(hash_name_expr)

            hash_urls_expr = parse("oracle_config.bitcoin_block_hash.url")
            self.check_valid_type(hash_urls_expr, str, key_required=True, value_default_allow=False)
            self.delete_key_safe(hash_urls_expr)

            hash_period_expr = parse("oracle_config.bitcoin_block_hash.collection_period_sec")
            self.check_valid_type(hash_period_expr, int, key_required=True, value_default_allow=False)
            self.delete_key_safe(hash_period_expr)
        self.raise_exception_if_not_empty(btc_hash_expr)

        price_expr = parse("oracle_config.asset_prices")
        self.check_valid_type(price_expr, dict, key_required=False, value_default_allow=False)
        if self.config["oracle_config"].get("asset_prices"):
            price_name_expr = parse("oracle_config.asset_prices.names")
            self.check_valid_type(price_name_expr, list, key_required=True, value_default_allow=False)
            self.delete_key_safe(price_name_expr)

            price_name_element_expr = parse("oracle_config.asset_prices.names[*]")
            self.check_valid_type(price_name_element_expr, Asset, is_enum=True)
            self.delete_key_safe(price_name_element_expr)

            price_period_expr = parse("oracle_config.asset_prices.collection_period_sec")
            self.check_valid_type(price_period_expr, int, key_required=True, value_default_allow=False)
            self.delete_key_safe(price_period_expr)

            price_urls = parse("oracle_config.asset_prices.urls")
            self.check_valid_type(price_urls, dict, key_required=True, value_default_allow=False)
            api_names = list(self.config["oracle_config"]["asset_prices"]["urls"].keys())
            for name in api_names:
                json_expr_child = parse("oracle_config.asset_prices.urls." + name)
                self.check_valid_type(json_expr_child, str, key_required=True, value_default_allow=False)
                self.delete_key_safe(json_expr_child)
            self.delete_key_safe(price_urls)
        self.raise_exception_if_not_empty(price_expr)

    def check_config(self):
        self.check_multichain_config()
        self.check_entity_config()
        self.check_oracle_config()

        for chain_name in self.supporting_chain_names:
            if self.config.get(chain_name) is None:
                raise Exception("The config of {} does not exists".format(chain_name))
            try:
                Chain[chain_name]
            except KeyError as e:
                json_expr = parse("{}".format(chain_name))
                raise InvalidEnum(json_expr, Chain, chain_name)

            self.check_chain_config(chain_name)
