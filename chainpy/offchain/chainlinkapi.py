import os
import unittest
from typing import List, Dict

from dotenv import load_dotenv

from chainpy.offchain.consts.chainlinkconst import ETH_CHAINLINK_SUPPORTING_SYMBOLS
from .priceapiabc import PriceApiABC, Symbol, QueryId, PriceVolume
from ..eth.managers.rpchandler import EthRpcClient
from ..eth.ethtype.amount import EthAmount
from bridgeconst.consts import Chain


class ChainlinkApi(PriceApiABC):
    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

        config_dict = {
            "ETH_MAIN": {"chain_name": "ETH_MAIN", "block_period_sec": 3, "url_with_access_key": api_base_url}
        }
        self.__rpc_cli = EthRpcClient.from_config_dict(config_dict, chain_index=Chain.ETH_MAIN)

    def ping(self) -> bool:
        return isinstance(self.__rpc_cli.chain_id, int)

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(ETH_CHAINLINK_SUPPORTING_SYMBOLS.keys())

    @staticmethod
    def _get_query_id_by_symbol(symbol: Symbol) -> QueryId:
        return ETH_CHAINLINK_SUPPORTING_SYMBOLS[symbol]

    def fetch_prices_with_volumes(self, symbols: List[Symbol]) -> Dict[Symbol, PriceVolume]:
        ret = {}
        for symbol in symbols:
            contract_address = ETH_CHAINLINK_SUPPORTING_SYMBOLS[symbol]
            if contract_address == "0x0000000000000000000000000000000000000000":
                raise Exception("Not supported symbol (zero address): {}".format(symbol))
            result = self.__rpc_cli.eth_call({"to": contract_address, "data": "0xfeaf968c"})
            price = EthAmount(int.from_bytes(result[32:64], byteorder="big"), 8)
            if ret.get(symbol) is not None:
                ret[symbol].append(price, EthAmount.zero())
            else:
                ret[symbol] = PriceVolume(symbol, price)
        return ret


class TestChainLinkApi(unittest.TestCase):
    def setUp(self) -> None:
        load_dotenv()
        self.api = ChainlinkApi(os.environ.get("ETHEREUM_MAINNET_ENDPOINT"))
        # Currently, The Chainlink(ETH) does not provide prices of BFC, BIFI
        self.symbols = ["ETH", "BNB", "MATIC", "USDC"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_supporting_symbol(self):
        symbols = self.api.supported_symbols()
        self.assertEqual(type(symbols), list)
        self.assertEqual(symbols, list(ETH_CHAINLINK_SUPPORTING_SYMBOLS.keys()))

    def test_price_and_volumes(self):
        symbol_to_pv = self.api.get_current_prices_with_volumes(self.symbols)
        for symbol, pv in symbol_to_pv.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(pv.price(), EthAmount))
            self.assertNotEqual(pv.price(), EthAmount.zero())
            self.assertTrue(isinstance(pv.volume(), EthAmount))
            self.assertEqual(pv.volume(), EthAmount.zero())

    def test_current_prices(self):
        prices_dict = self.api.get_current_prices(self.symbols)
        for symbol, price in prices_dict.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(price, EthAmount))
            self.assertNotEqual(price, EthAmount.zero())
