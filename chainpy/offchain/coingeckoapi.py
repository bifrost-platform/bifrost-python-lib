import unittest
from typing import List, Tuple

from ..eth.ethtype.amount import EthAmount
from chainpy.offchain.consts.coingeckoconst import COINGECKO_SUPPORTING_SYMBOLS
from ..offchain.priceapiabc import PriceApiABC, Market, Symbol, QueryId


class CoingeckoApi(PriceApiABC):
    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

    def ping(self) -> bool:
        api_url = "{}ping".format(self.base_url)
        result = self._request(api_url)
        return result == {"gecko_says": "(V3) To the Moon!"}

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(COINGECKO_SUPPORTING_SYMBOLS.keys())

    @staticmethod
    def _get_query_id_by_symbol(symbol: Symbol) -> QueryId:
        return COINGECKO_SUPPORTING_SYMBOLS[symbol]

    def _fetch_markets_by_symbols(self, symbols: List[Symbol]) -> List[Market]:
        # get not cached coin id
        market_ids = [self._get_query_id_by_symbol(symbol) for symbol in symbols]
        req_ids = ",".join(market_ids)
        api_url = "{}coins/markets".format(self.base_url)

        return self._request(api_url, {"ids": req_ids, "vs_currency": "usd"})

    @staticmethod
    def _parse_price_and_volume_in_markets(market_id: str, markets: List[Market]) -> Tuple[EthAmount, EthAmount]:
        for market in markets:
            if market["id"] == market_id:
                price, volume = market["current_price"], market["total_volume"]
                if isinstance(price, int):
                    price = float(price)
                if isinstance(volume, int):
                    volume = float(volume)
                return EthAmount(price), EthAmount(volume)
        return EthAmount.zero(), EthAmount.zero()

    @staticmethod
    def _calc_price_and_volume_in_usd(symbol: Symbol, markets: list) -> Tuple[EthAmount, EthAmount]:
        market_id = COINGECKO_SUPPORTING_SYMBOLS[symbol]
        return CoingeckoApi._parse_price_and_volume_in_markets(market_id, markets)


class TestCoinGeckoApi(unittest.TestCase):
    def setUp(self) -> None:
        # Open api url
        self.api = CoingeckoApi("https://api.coingecko.com/api/v3/")
        self.symbols = ["BFC", "ETH", "BNB", "MATIC", "USDC", "BIFI"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_supporting_symbol(self):
        symbols = self.api.supported_symbols()
        self.assertEqual(type(symbols), list)
        self.assertEqual(symbols, list(COINGECKO_SUPPORTING_SYMBOLS.keys()))

    def test_price_and_volumes(self):
        symbol_to_pv = self.api.get_current_prices_with_volumes(self.symbols)
        for symbol, pv in symbol_to_pv.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(pv.price(), EthAmount))
            self.assertNotEqual(pv.price(), EthAmount.zero())
            self.assertTrue(isinstance(pv.volume(), EthAmount))
            self.assertNotEqual(pv.volume(), EthAmount.zero())

    def test_current_prices(self):
        prices_dict = self.api.get_current_prices(self.symbols)
        for symbol, price in prices_dict.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(price, EthAmount))
            self.assertNotEqual(price, EthAmount.zero())
