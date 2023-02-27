import json
import unittest

from chainpy.eth.managers.configsanitycheck import ConfigSanityChecker
from chainpy.eth.managers.utils import merge_dict

config_fixture = {
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
        "transaction_block_delay": 5,
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

        ],
        "events": [

        ]
    },
    "ETH_GOERLI": {
        "chain_name": "ETH_GOERLI",
        "block_period_sec": 13,
        "url_with_access_key": "a",
        "bootstrap_latest_height": 7749286,
        "block_aging_period": 2,
        "transaction_block_delay": 5,
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
            {
                "name": "relayer_authority", "address": "0xF51f7e267D2D966f8d3Ff2fea42B410bB14800e1",
                "abi_file": "abi.relayer.external.json", "deploy_height": 8052946
            },
            {
                "name": "vault", "address": "0x7EB02c73349B3De1406e6b433c5bA1a526CBF253",
                "abi_file": "abi.vault.external.json", "deploy_height": 8052948
            },
            {
                "name": "socket", "address": "0xeF5260Db045200142a6B5DDB297e860099ffd51d",
                "abi_file": "abi.socket.external.json", "deploy_height": 8052951
            },
            {
                "name": "BFC_ON_ETH_GOERLI", "address": "0x3A815eBa66EaBE966a6Ae7e5Df9652eca24e9c54",
                "abi_file": "abi.erc20.json"
            },
            {
                "name": "BIFI_ON_ETH_GOERLI", "address": "0x055ED934c426855caB467FdF8441D4FD6a7D2659",
                "abi_file": "abi.erc20.json"
            },
            {
                "name": "USDC_ON_ETH_GOERLI", "address": "0xD978Be30CE95D42DF7067b988f25bCa2b286Fb70",
                "abi_file": "abi.erc20.json"
            }
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
        "transaction_block_delay": 5,
        "receipt_max_try": 20,
        "max_log_num": 1000,
        "rpc_server_downtime_allow_sec": 180,
        "fee_config": {
            "type": 0,
            "gas_price": 2000000000000
        },
        "abi_dir": "configs/",
        "contracts": [
            {
                "name": "relayer_authority", "address": "0xCf9f6428A309b6652a1dfaA4d8aB8B61C9c7E8CF",
                "abi_file": "abi.relayer.external.json", "deploy_height": 25067012
            },
            {
                "name": "vault", "address": "0x27C66cb5caa07C9B332939c357c789C606f5054C",
                "abi_file": "abi.vault.external.json", "deploy_height": 25067016
            },
            {
                "name": "socket", "address": "0x8039c3AD8ED55509fD3f6Daa78867923fDe6E61c",
                "abi_file": "abi.socket.external.json", "deploy_height": 25067020
            },
            {
                "name": "USDC_ON_BNB_TEST", "address": "0xC9C0aD3179eE2f4801454926ED5D6A2Da30b56FB",
                "abi_file": "abi.erc20.json"
            }
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
        "transaction_block_delay": 5,
        "receipt_max_try": 20,
        "max_log_num": 1000,
        "rpc_server_downtime_allow_sec": 180,
        "fee_config": {
            "type": 2,
            "max_gas_price": 2000000000000,
            "max_priority_price": 1000000000000
        },
        "abi_dir": "configs/", "contracts": [
            {
                "name": "relayer_authority", "address": "0x2FD5232fDFa6e1c127e7821CC48108Ca79281a38",
                "abi_file": "abi.relayer.external.json", "deploy_height": 28954662
            },
            {
                "name": "vault", "address": "0xB2ba0020560cF6c164DC48D1E29559AbA8472208",
                "abi_file": "abi.vault.external.json", "deploy_height": 30814945
            },
            {
                "name": "socket", "address": "0xA25357F3C313Bd13885678f935178211f0dF6722",
                "abi_file": "abi.socket.external.json", "deploy_height": 30814949
            }
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
        "slow_relayer_delay_sec": 180,
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


class TestConfigSanityCheck1(unittest.TestCase):
    def setUp(self) -> None:
        with open("configs-testnet/entity.relayer.json", "r") as f:
            config = json.load(f)
        with open("configs-testnet/entity.relayer.private.json", "r") as f:
            private_config = json.load(f)
        config_from_file = merge_dict(config, private_config)
        self.checker = ConfigSanityChecker(config_from_file)

    def test_sanity_check(self):
        self.checker.check_config()
        ConfigSanityChecker(config_fixture).check_config()
