import json
import unittest

from chainpy.eth.managers.configsanitycheck import ConfigChecker


class TestConfigSanityCheck(unittest.TestCase):
    def setUp(self) -> None:
        with open("./data/entity.entity.template.json", "r") as f:
            self.config = json.load(f)

    def test_sanity_check(self):
        ConfigChecker.check_config(self.config)
