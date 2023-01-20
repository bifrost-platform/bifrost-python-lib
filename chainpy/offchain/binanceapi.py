import unittest
from typing import List, Dict
from urllib import parse
import requests

from .consts.binanceconst import BINANCE_SUPPORTING_SYMBOLS
from ..eth.ethtype.amount import EthAmount
from ..offchain.priceapiabc import PriceApiABC, Symbol, PriceVolume, QueryId, Market


# https://api.binance.com/api/v1/ticker/allPrices
# https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BNBUSDT%22,%22BNBBTC%22]
class BinanceApi(PriceApiABC):
    ANCHOR_SYMBOLS = ["BTC", "ETH", "USDT", "USDC", "BNB", "TUSD", "PAX", "USDC", "BUSD"]

    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

    def ping(self) -> bool:
        api_url = "{}ping".format(self.base_url)
        result = self._request(api_url)
        return result == dict()

    @staticmethod
    def is_anchor(symbol: Symbol) -> bool:
        return symbol in BinanceApi.ANCHOR_SYMBOLS

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(BINANCE_SUPPORTING_SYMBOLS.keys())

    @staticmethod
    def _get_query_ids(symbol: Symbol) -> List[QueryId]:
        if symbol == "USDT":
            return []
        else:
            anchors = BINANCE_SUPPORTING_SYMBOLS[symbol]
            return ["{}{}".format(symbol, anchor) for anchor in anchors]

    def _fetch_markets_by_symbols(self, symbols: List[Symbol]) -> List[Market]:
        anchors = list()
        for symbol in symbols:
            anchors += BINANCE_SUPPORTING_SYMBOLS[symbol]

        query_ids = []
        for symbol in symbols + anchors:
            query_ids += self._get_query_ids(symbol)

        query_ids = sorted(list(set(query_ids)))  # remove duplication
        api_url = "{}ticker/24hr".format(self.base_url)
        return self._request(api_url, {"symbols": query_ids})

    def fetch_prices_with_volumes(self, symbols: List[Symbol]) -> Dict[Symbol, PriceVolume]:
        pass


class TestBinanceApi(unittest.TestCase):
    def setUp(self) -> None:
        # Open api url
        self.api = BinanceApi("https://api.binance.com/api/v3/")

        # Currently, The Binance does not provide prices of BFC, BIFI
        self.symbols = ["ETH", "BNB", "MATIC", "USDC"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_supporting_symbol(self):
        symbols = self.api.supported_symbols()
        self.assertEqual(type(symbols), list)
        self.assertEqual(symbols, list(BINANCE_SUPPORTING_SYMBOLS.keys()))

    def test_current_prices_with_volumes(self):
        # result = self.api._fetch_markets_by_symbols(self.symbols)
        # print(result)


        url = parse.urlparse("https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BNBBTC%22,%22BNBBUSD%22]")
        base_url = url.scheme + "://" + url.hostname + url.path + "?"
        print("url: {}".format(base_url + url.query))
        result = requests.get(base_url + url.query)
        print(result)

        print(url.scheme, url.netloc, url.hostname, url.path)

        query = parse.urlencode({"symbols": ["ETHBTC", "ETHTUSD"]}, doseq=False, encoding="UTF-8")
        print(query)
        # result = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbols=[%22ETHBTC%22,%22ETHTUSD%22]")
        # print(result)


    # def test_current_prices_with_volumes(self):
    #     ids = ["bifrost"]
    #     prices_and_volume_dict = self.api.get_current_price_and_volume(ids)
    #     for coin_id, price_and_volume in prices_and_volume_dict.items():
    #         self.assertTrue(coin_id in ids)
    #         self.assertEqual(type(price_and_volume.price), EthAmount)
    #         self.assertEqual(type(price_and_volume._volumes), EthAmount)

    # def test_price(self):
    #     ids = ["BFC", "BTC", "FIL"]
    #     prices_dict = self.api.get_current_price(ids)
    #     for coin_id, price in prices_dict.items():
    #         self.assertTrue(coin_id in ids)
    #         self.assertEqual(type(price), EthAmount)
