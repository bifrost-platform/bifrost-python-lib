import json
import unittest

from chainpy.eth.managers.configsanitycheck import ConfigChecker
from chainpy.eth.managers.utils import merge_dict


class TestConfigSanityCheck(unittest.TestCase):
    def setUp(self) -> None:
        with open("configs-testnet/entity.relayer.json", "r") as f:
            config = json.load(f)
        with open("configs-testnet/entity.relayer.private.json", "r") as f:
            private_config = json.load(f)
        self.config = merge_dict(config, private_config)

    def test_sanity_check(self):
        ConfigChecker.check_config(self.config)
