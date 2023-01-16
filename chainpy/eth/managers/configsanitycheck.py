import copy
import unittest
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
        check_valid_type(chain_config, "block_period_sec", expected_type=int, required=True, default_allow=False)
        delete_key_safe(chain_config, "block_period_sec")
        check_valid_type(chain_config, "block_aging_period", expected_type=int, required=True, default_allow=False)
        delete_key_safe(chain_config, "block_aging_period")

        check_valid_type(chain_config, "bootstrap_latest_height", expected_type=int)
        delete_key_safe(chain_config, "bootstrap_latest_height")
        check_valid_type(chain_config, "transaction_commit_multiplier", expected_type=int, default_allow=False)
        delete_key_safe(chain_config, "transaction_commit_multiplier")
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
        delete_key_safe(config, "role")

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


class TestConfigChecker(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "oracle_config": {
                "bitcoin_block_hash": {
                    "name": "BITCOIN_BLOCK_HASH",
                    "url": "a",
                    "collection_period_sec": 300
                },
                "asset_prices": {
                    "names": [
                        "ETH_ON_ETH_MAIN",
                        "BFC_ON_ETH_MAIN",
                        "BNB_ON_BNB_MAIN",
                        "USDC_ON_ETH_MAIN",
                        "BIFI_ON_ETH_MAIN"
                    ],
                    "collection_period_sec": 120,
                    "urls": {
                        "Coingecko": "a",
                        "Upbit": "a",
                        "Chainlink": "a"
                    }
                }
            },
             "BFC_TEST": {
                "chain_name": "BFC_TEST",
                "block_period_sec": 3,
                "url_with_access_key": "a",
                "bootstrap_latest_height": 2883,
                "block_aging_period": 2,
                "transaction_commit_multiplier": 2,
                "receipt_max_try": 20,
                "max_log_num": 1000,
                "rpc_server_downtime_allow_sec": 180,
                "fee_config": {
                    "type": 2,
                    "max_gas_price": 5000000000000,
                    "max_priority_price": 1000000000000
                },
                "abi_dir": "configs/",
                "contracts": [
                    {"name": "authority", "address": "0x0000000000000000000000000000000000000400", "abi_file": "abi.authority.bifrost.json", "deploy_height": 1426518},
                    {"name": "relayer_authority", "address": "0x0000000000000000000000000000000000002000", "abi_file": "abi.relayer.bifrost.json", "deploy_height": 1426518},
                    {"name": "vault", "address": "0x90381bB369D4F8069fdA9246b23637a78c5d1c83", "abi_file": "abi.vault.bifrost.json", "deploy_height": 1426522},
                    {"name": "socket", "address": "0x0218371b18340aBD460961bdF3Bd5F01858dAB53", "abi_file": "abi.socket.bifrost.json", "deploy_height": 1426524},
                    {"name": "oracle", "address": "0x252a402B80d081F672e7874E94214054FdB78C77", "abi_file": "abi.oracle.bifrost.json", "deploy_height": 2057990},
                    {"name": "BRIDGED_ETH_GOERLI_BFC_ON_BFC_TEST", "address": "0xfB5D65B8e8784ae3e004e1e476B05d408e6A1f2D", "abi_file": "abi.erc20.json"},
                    {"name": "BRIDGED_ETH_GOERLI_ETH_ON_BFC_TEST", "address": "0xD089773D293F43440529e6cfa84639E0498A0277", "abi_file": "abi.erc20.json"},
                    {"name": "BRIDGED_ETH_GOERLI_BIFI_ON_BFC_TEST", "address": "0xC4F1CcafCBeB0BE0F1CDBA499696603528655F29", "abi_file": "abi.erc20.json"},
                    {"name": "BRIDGED_ETH_GOERLI_USDC_ON_BFC_TEST", "address": "0xa7bb0a2693fb4d1ab9a6C5acCf5C63f12fab1855", "abi_file": "abi.erc20.json"},
                    {"name": "BRIDGED_BNB_TEST_USDC_ON_BFC_TEST", "address": "0xC67f0b7c01f6888D43B563B3a8B851856BcfAB64", "abi_file": "abi.erc20.json"},
                    {"name": "BRIDGED_BNB_TEST_BNB_ON_BFC_TEST", "address": "0x72D22DF54b86d25D9F9E0C10D516Ab22517b7051", "abi_file": "abi.erc20.json"},
                    {"name": "BRIDGED_MATIC_MUMBAI_MATIC_ON_BFC_TEST", "address": "0x82c1aD3aF709210F203869a03CdE8C7d0b9841d8", "abi_file": "abi.erc20.json"},
                    {"name": "UNIFIED_BFC_ON_BFC_TEST", "address": "0xB0fF18CB2d0F3f51a9c54Af862ed98f3caa027A1", "abi_file": "abi.unified.coin.json"},
                    {"name": "UNIFIED_BIFI_ON_BFC_TEST", "address": "0x8010a873d59719e895E20f15f9906B5a1F399C3A", "abi_file": "abi.unified.erc20.json"},
                    {"name": "UNIFIED_BNB_ON_BFC_TEST", "address": "0xCd8bf79fA84D551f2465C0a646cABc295d43Be5C", "abi_file": "abi.unified.erc20.json"},
                    {"name": "UNIFIED_ETH_ON_BFC_TEST", "address": "0xc83EEd1bf5464eD5383bc3342b918E08f6815950", "abi_file": "abi.unified.erc20.json"},
                    {"name": "UNIFIED_USDC_ON_BFC_TEST", "address": "0x28661511CDA7119B2185c647F23106a637CC074f", "abi_file": "abi.unified.erc20.json"},
                    {"name": "UNIFIED_MATIC_ON_BFC_TEST", "address": "0xad115F901a1Af99dc83D055C89641031fd1a50Dc", "abi_file": "abi.unified.erc20.json"}
                ],
                "events": [
                    {
                        "contract_name": "socket",
                        "event_name": "Socket"
                    },
                    {
                        "contract_name": "socket",
                        "event_name": "RoundUp"
                    }
                ]
            },
            "ETH_GOERLI": {
                "chain_name": "ETH_GOERLI",
                "block_period_sec": 13,
                "url_with_access_key": "a",
                "bootstrap_latest_height": 7749286,
                "block_aging_period": 2,
                "transaction_commit_multiplier": 2,
                "receipt_max_try": 20,
                "max_log_num": 1000,
                "rpc_server_downtime_allow_sec": 180,
                "fee_config": {
                    "type": 2,
                    "max_gas_price": 2000000000000,
                    "max_priority_price": 1000000000000
                },
                "abi_dir": "configs/",
                "contracts": [
                    {"name": "relayer_authority", "address": "0xF51f7e267D2D966f8d3Ff2fea42B410bB14800e1", "abi_file": "abi.relayer.external.json", "deploy_height": 8052946},
                    {"name": "vault", "address": "0x7EB02c73349B3De1406e6b433c5bA1a526CBF253", "abi_file": "abi.vault.external.json", "deploy_height": 8052948},
                    {"name": "socket", "address": "0xeF5260Db045200142a6B5DDB297e860099ffd51d", "abi_file": "abi.socket.external.json", "deploy_height": 8052951},
                    {"name": "BFC_ON_ETH_GOERLI", "address": "0x3A815eBa66EaBE966a6Ae7e5Df9652eca24e9c54", "abi_file": "abi.erc20.json"},
                    {"name": "BIFI_ON_ETH_GOERLI", "address": "0x055ED934c426855caB467FdF8441D4FD6a7D2659", "abi_file": "abi.erc20.json"},
                    {"name": "USDC_ON_ETH_GOERLI", "address": "0xD978Be30CE95D42DF7067b988f25bCa2b286Fb70", "abi_file": "abi.erc20.json"}
                ],
                "events": [
                    {
                        "contract_name": "socket",
                        "event_name": "Socket"
                    }
                ]
            },
            "BNB_TEST": {
                "chain_name": "BNB_TEST",
                "block_period_sec": 3,
                "url_with_access_key": "a",
                "bootstrap_latest_height": 23601374,
                "block_aging_period": 5,
                "transaction_commit_multiplier": 2,
                "receipt_max_try": 20,
                "max_log_num": 1000,
                "rpc_server_downtime_allow_sec": 180,
                "fee_config": {
                    "type": 0,
                    "gas_price": 2000000000000
                },
                "abi_dir": "configs/",
                "contracts": [
                    {"name": "relayer_authority", "address": "0xCf9f6428A309b6652a1dfaA4d8aB8B61C9c7E8CF", "abi_file": "abi.relayer.external.json", "deploy_height": 25067012},
                    {"name": "vault", "address": "0x27C66cb5caa07C9B332939c357c789C606f5054C", "abi_file": "abi.vault.external.json", "deploy_height": 25067016},
                    {"name": "socket", "address": "0x8039c3AD8ED55509fD3f6Daa78867923fDe6E61c", "abi_file": "abi.socket.external.json", "deploy_height": 25067020},
                    {"name": "USDC_ON_BNB_TEST", "address": "0xC9C0aD3179eE2f4801454926ED5D6A2Da30b56FB", "abi_file": "abi.erc20.json"}
                ],
                "events": [
                    {
                        "contract_name": "socket",
                        "event_name": "Socket"
                    }
                ]
            },
            "MATIC_MUMBAI": {
                "chain_name": "MATIC_MUMBAI",
                "block_period_sec": 2,
                "url_with_access_key": "a",
                "bootstrap_latest_height": 30814949,
                "block_aging_period": 3,
                "transaction_commit_multiplier": 2,
                "receipt_max_try": 20,
                "max_log_num": 1000,
                "rpc_server_downtime_allow_sec": 180,
                "fee_config": {
                    "type": 2,
                    "max_gas_price": 2000000000000,
                    "max_priority_price": 1000000000000
                },
                "abi_dir": "configs/",
                "contracts": [
                    {"name": "relayer_authority", "address": "0x2FD5232fDFa6e1c127e7821CC48108Ca79281a38", "abi_file": "abi.relayer.external.json", "deploy_height": 28954662},
                    {"name": "vault", "address": "0xB2ba0020560cF6c164DC48D1E29559AbA8472208", "abi_file": "abi.vault.external.json", "deploy_height": 30814945},
                    {"name": "socket", "address": "0xA25357F3C313Bd13885678f935178211f0dF6722", "abi_file": "abi.socket.external.json", "deploy_height": 30814949}
                ],
                "events": [
                    {
                        "contract_name": "socket",
                        "event_name": "Socket"
                    }
                ]
            },
            "entity": {
                "role": "slow-relayer",
                "account_name": "relayer-launched-on-console",
                "secret_hex": "",
                "supporting_chains": [
                    "BFC_TEST",
                    "ETH_GOERLI",
                    "BNB_TEST",
                    "MATIC_MUMBAI"
                ]
            },
            "multichain_config": {
                "chain_monitor_period_sec": 20
            }
        }

    def test_check_chain_name(self):
        ConfigChecker.check_config(self.config)
