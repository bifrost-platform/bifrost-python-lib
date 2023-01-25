import unittest
from typing import List, Dict, Tuple

from .consts.binanceconst import BINANCE_SUPPORTING_SYMBOLS
from ..eth.ethtype.amount import EthAmount, eth_amount_weighted_sum, eth_amount_sum
from ..offchain.priceapiabc import PriceApiABC, Symbol, PriceVolume, QueryId, Market


# https://api.binance.com/api/v1/ticker/allPrices
# https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BNBUSDT%22,%22BNBBTC%22]
class BinanceApi(PriceApiABC):
    ANCHOR_SYMBOLS = ["BTC", "ETH", "USDT", "BNB", "BUSD"]

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

        joined_query_id = "[%22" + "%22,%22".join(query_ids) + "%22]"
        return self._request(api_url, {"symbols": joined_query_id})

    @staticmethod
    def _parse_price_and_volume_in_markets(market_id: str, markets: List[Market]) -> Tuple[EthAmount, EthAmount]:
        for market in markets:
            if market["symbol"] == market_id:
                price, volume = market["lastPrice"], market["volume"]
                return EthAmount(price), EthAmount(volume)
        return EthAmount.zero(), EthAmount.zero()

    @staticmethod
    def _calc_price_and_volume_in_usd(symbol: Symbol, markets: List[Market]) -> Tuple[EthAmount, EthAmount]:
        if symbol == "USDT":
            return EthAmount("1.0", 18), EthAmount.zero()  # TODO usdt volume zero?

        else:
            market_prices, market_volumes = list(), list()
            for anchor in BINANCE_SUPPORTING_SYMBOLS[symbol]:
                anchor_price, _ = BinanceApi._calc_price_and_volume_in_usd(anchor, markets)
                target_price, target_volume = BinanceApi._parse_price_and_volume_in_markets(
                    "{}{}".format(symbol, anchor), markets)
                market_prices.append(target_price * anchor_price)
                market_volumes.append(target_volume * anchor_price)

            weighted_price = eth_amount_weighted_sum(market_prices, market_volumes)
            return weighted_price, eth_amount_sum(market_volumes)

    def fetch_prices_with_volumes(self, symbols: List[Symbol]) -> Dict[Symbol, PriceVolume]:
        markets = self._fetch_markets_by_symbols(symbols)

        ret = {}
        for symbol in symbols:
            price, volume = self._calc_price_and_volume_in_usd(symbol, markets)
            if ret.get(symbol) is not None:
                ret[symbol].append(price, volume)
            else:
                ret[symbol] = PriceVolume(symbol, price, volume)
        return ret


class TestBinanceApi(unittest.TestCase):
    def setUp(self) -> None:
        # Open api url
        self.api = BinanceApi("https://api.binance.com/api/v3/")

        # Currently, The Binance does not provide prices of BFC, BIFI, USDC
        self.symbols = ["ETH", "BNB", "MATIC"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_supporting_symbol(self):
        symbols = self.api.supported_symbols()
        self.assertEqual(type(symbols), list)
        self.assertEqual(symbols, list(BINANCE_SUPPORTING_SYMBOLS.keys()))

    def test_current_prices_with_volumes(self):
        symbol_to_pv = self.api.get_current_prices_with_volumes(self.symbols)
        for symbol, pv in symbol_to_pv.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(pv.price(), EthAmount))
            self.assertNotEqual(pv.price(), EthAmount.zero())
            self.assertTrue(isinstance(pv.volume(), EthAmount))
            if symbol == "USDT":
                self.assertEqual(pv.volume(), EthAmount.zero())
            else:
                self.assertNotEqual(pv.volume(), EthAmount.zero())

    def test_current_prices(self):
        prices_dict = self.api.get_current_prices(self.symbols)
        for symbol, price in prices_dict.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(price, EthAmount))
            self.assertNotEqual(price, EthAmount.zero())
