import copy
import bridgeconst.consts


class ConfigCheckerError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


def is_default(item) -> bool:
    return item == type(item)()


def is_none(item) -> bool:
    return item is None


def is_meaningful(item) -> bool:
    return False if is_none(item) else False if is_default(item) else True


def assert_not_default(item, name):
    if is_default(item):
        raise ConfigCheckerError("\"{}\" should be meaningful".format(name))


def assert_required(item, name, default_allow: bool = True):
    if item is None:
        raise ConfigCheckerError("\"{}\" is required".format(name))
    if not default_allow:
        assert_not_default(item, name)


def assert_enum(name: str, expected_enum_type: type):
    try:
        _enum = expected_enum_type[name]
    except Exception as e:
        raise ConfigCheckerError("Invalid enum: enum_type({}), name({})".format(expected_enum_type.__name__, name))


def check_valid_type(
        config: dict,
        name: str,
        expected_type: type,
        is_enum: bool = False,
        required: bool = False,
        default_allow: bool = True
):
    item = config.get(name)
    if required:
        assert_required(item, name, default_allow=default_allow)

    if not default_allow:
        assert_not_default(item, name)

    if item is None:
        # does not necessary to check type if item is None
        return

    if is_enum:
        assert_enum(item, expected_type)
    else:
        if not isinstance(item, expected_type):
            msg = "Not expected type: expected({}), actual({})".format(expected_type, type(item))
            raise ConfigCheckerError(msg)


def delete_key_safe(config: dict, key: str):
    if config.get(key) is not None:
        del config[key]


class ChainConfigChecker:
    @staticmethod
    def check_config(chain_config: dict):
        check_valid_type(
            chain_config, "chain_name", expected_type=bridgeconst.consts.Chain, is_enum=True, required=True
        )
        delete_key_safe(chain_config, "chain_name")
        check_valid_type(chain_config, "url_with_access_key", expected_type=str, required=True, default_allow=False)
        delete_key_safe(chain_config, "url_with_access_key")
        check_valid_type(chain_config, "block_period_sec", expected_type=int, required=False, default_allow=False)
        delete_key_safe(chain_config, "block_period_sec")
        check_valid_type(chain_config, "block_aging_period", expected_type=int, required=False, default_allow=False)
        delete_key_safe(chain_config, "block_aging_period")

        check_valid_type(chain_config, "bootstrap_latest_height", expected_type=int)
        delete_key_safe(chain_config, "bootstrap_latest_height")
        check_valid_type(chain_config, "transaction_block_delay", expected_type=int, default_allow=False)
        delete_key_safe(chain_config, "transaction_block_delay")
        check_valid_type(chain_config, "receipt_max_try", expected_type=int, default_allow=False)
        delete_key_safe(chain_config, "receipt_max_try")
        check_valid_type(chain_config, "max_log_num", expected_type=int, default_allow=False)
        delete_key_safe(chain_config, "max_log_num")
        check_valid_type(chain_config, "rpc_server_downtime_allow_sec", expected_type=int, default_allow=False)
        delete_key_safe(chain_config, "rpc_server_downtime_allow_sec")
        check_valid_type(chain_config, "abi_dir", str, default_allow=True)
        delete_key_safe(chain_config, "abi_dir")

        ChainConfigChecker.check_contracts(chain_config)
        ChainConfigChecker.check_events(chain_config)
        delete_key_safe(chain_config, "contracts")
        delete_key_safe(chain_config, "events")

        ChainConfigChecker.check_fee_config(chain_config)
        delete_key_safe(chain_config, "fee_config")

        if len(chain_config.keys()) != 0:
            raise ConfigCheckerError("An unsupported config exists.: {}".format(chain_config.keys()))

    @staticmethod
    def check_fee_config(config: dict):
        check_valid_type(config, "fee_config", dict, required=False, default_allow=False)

        fee_config = config["fee_config"]
        check_valid_type(fee_config, "type", int, required=True, default_allow=True)
        if fee_config["type"] == 0:
            check_valid_type(fee_config, "gas_price", int, required=True)
        elif 0 < fee_config["type"] <= 2:
            check_valid_type(fee_config, "max_gas_price", int, required=True)
            check_valid_type(fee_config, "max_priority_price", int, required=True)
        else:
            raise ConfigCheckerError("Invalid type of fee_config: {}".format(fee_config["type"]))

    @staticmethod
    def check_contracts(config: dict):
        check_valid_type(config, "contracts", list)

        contracts_config_list = config.get("contracts")
        if not is_meaningful(contracts_config_list):
            return

        for contract_config in contracts_config_list:
            check_valid_type(contract_config, "name", str, required=True, default_allow=False)
            check_valid_type(contract_config, "address", str, required=True, default_allow=False)
            check_valid_type(contract_config, "abi_file", str, required=True, default_allow=False)
            check_valid_type(contract_config, "deploy_height", int, required=False)

    @staticmethod
    def check_events(config: dict):
        check_valid_type(config, "events", list)

        event_config_list = config.get("events")
        if not is_meaningful(event_config_list):
            return

        contract_config_list = config.get("contracts")
        if contract_config_list is None:
            raise ConfigCheckerError("There is no contract to which the event belongs.")

        for event_config in event_config_list:
            check_valid_type(event_config, "contract_name", str, required=True, default_allow=False)
            check_valid_type(event_config, "event_name", str, required=True, default_allow=False)

            pass_flag = False
            for contract in contract_config_list:
                if contract["name"] == event_config["contract_name"]:
                    pass_flag = True
            if not pass_flag:
                raise ConfigCheckerError(
                    "There is no contract to which the event belongs.: {}".format(event_config["event_name"])
                )


class OracleConfigChecker:
    @staticmethod
    def check_config(config: dict):
        check_valid_type(config, "bitcoin_block_hash", dict, required=True, default_allow=True)
        btc_oracle_config = config["bitcoin_block_hash"]
        if is_meaningful(btc_oracle_config):
            check_valid_type(
                btc_oracle_config,
                "name",
                bridgeconst.consts.Oracle,
                is_enum=True,
                required=True,
                default_allow=False
            )
            delete_key_safe(btc_oracle_config, "name")

            check_valid_type(btc_oracle_config, "url", str, required=True, default_allow=False)
            delete_key_safe(btc_oracle_config, "url")
            check_valid_type(btc_oracle_config, "collection_period_sec", int, required=True, default_allow=False)
            delete_key_safe(btc_oracle_config, "collection_period_sec")
            if len(btc_oracle_config.keys()) != 0:
                raise ConfigCheckerError("An unsupported config exists.: {}".format(btc_oracle_config.keys()))
        delete_key_safe(config, "bitcoin_block_hash")

        check_valid_type(config, "asset_prices", dict, required=False, default_allow=True)
        price_oracle_config = config["asset_prices"]
        if is_meaningful(price_oracle_config):
            check_valid_type(price_oracle_config, "names", list, required=True, default_allow=False)
            for name in price_oracle_config["names"]:
                assert_enum(name, bridgeconst.consts.Asset)
            delete_key_safe(price_oracle_config, "names")

            check_valid_type(price_oracle_config, "collection_period_sec", int, required=True, default_allow=False)
            delete_key_safe(price_oracle_config, "collection_period_sec")

            check_valid_type(price_oracle_config, "urls", dict, required=True, default_allow=False)
            for source_name in price_oracle_config["urls"].keys():
                check_valid_type(price_oracle_config["urls"], source_name, str, required=True, default_allow=False)
            delete_key_safe(price_oracle_config, "urls")
            if len(price_oracle_config.keys()) != 0:
                raise ConfigCheckerError("An unsupported config exists.: {}".format(price_oracle_config.keys()))

        delete_key_safe(config, "asset_prices")
        if len(config.keys()) != 0:
            raise ConfigCheckerError("An unsupported config exists.: {}".format(config.keys()))


class EntityConfigChecker:
    @staticmethod
    def check_config(config: dict):
        check_valid_type(config, "role", str, required=True, default_allow=False)
        roles = ["User", "Relayer", "Fast-relayer", "Slow-relayer"]
        if config["role"].capitalize() not in roles:
            raise ConfigCheckerError("Invalid entity's role: {}".format(config["role"]))

        if config["role"] == "slow-relayer":
            check_valid_type(config, "slow_relayer_delay_sec", int, required=True, default_allow=False)
        else:
            check_valid_type(config, "slow_relayer_delay_sec", int, required=False, default_allow=True)
        delete_key_safe(config, "role")
        delete_key_safe(config, "slow_relayer_delay_sec")

        check_valid_type(config, "account_name", str, required=False, default_allow=True)
        delete_key_safe(config, "account_name")

        check_valid_type(config, "secret_hex", str, required=False, default_allow=True)
        delete_key_safe(config, "secret_hex")

        check_valid_type(config, "supporting_chains", list, required=True, default_allow=False)
        for chain_name in config["supporting_chains"]:
            assert_enum(chain_name, bridgeconst.consts.Chain)

        delete_key_safe(config, "supporting_chains")

        if len(config.keys()) != 0:
            raise ConfigCheckerError("An unsupported config exists.: {}".format(config.keys()))


class ConfigChecker:
    @staticmethod
    def check_config(config: dict):
        check_valid_type(config, "multichain_config", dict, required=True, default_allow=False)
        check_valid_type(
            config["multichain_config"],
            "chain_monitor_period_sec",
            int,
            required=True,
            default_allow=False
        )
        delete_key_safe(config, "multichain_config")

        check_valid_type(config, "entity", dict, required=True, default_allow=False)
        EntityConfigChecker.check_config(config["entity"])
        delete_key_safe(config, "entity")

        check_valid_type(config, "oracle_config", dict, required=False, default_allow=True)
        OracleConfigChecker.check_config(config["oracle_config"])
        delete_key_safe(config, "oracle_config")

        config_clone = copy.deepcopy(config)
        for chain_name in config_clone.keys():
            assert_enum(chain_name, bridgeconst.consts.Chain)
            ChainConfigChecker.check_config(config[chain_name])
            delete_key_safe(config, chain_name)

        if len(config.keys()) != 0:
            raise ConfigCheckerError("An unsupported config exists.: {}".format(config.keys()))
