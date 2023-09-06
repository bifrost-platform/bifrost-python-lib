import unittest
from typing import List, Dict, Tuple

from .consts.binanceconst import BINANCE_SYMBOL_TO_ANCHORS
from .utils import restore_replace
from ..eth.ethtype.amount import EthAmount, eth_amount_weighted_sum, eth_amount_sum
from ..offchain.priceapiabc import PriceApiABC, Symbol, PriceVolume, QueryId, QueriedData, Price, Volume, AnchorSymbol

f"""
Binance API Client
- open api url: https://api.binance.com/api/v1/
- getting all prices: https://api.binance.com/api/v1/ticker/allPrices
- getting information of specific asset: https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BNBUSDT%22,%22BNBBTC%22]

Definitions. 
- Symbol: symbol of the asset.
- PairId: unique name of the asset pair; SYMBOL | ANCHOR_SYMBOL; e.g.) BTCUSDT, ETHBTC
- PairData: information(dictionary) of the pair.  
- MarketSymbol: symbol of the market.
"""


class BinanceApi(PriceApiABC):
    MARKET_SYMBOLS = ["BTC", "ETH", "USDT", "BNB", "BUSD"]
    SYMBOL_REPLACE_MAP = {}

    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

    def ping(self) -> bool:
        api_url = "{}ping".format(self.base_url)
        result = self._request(api_url)
        return result == dict()

    @staticmethod
    def is_anchor(symbol: Symbol) -> bool:
        return symbol in BinanceApi.MARKET_SYMBOLS

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(restore_replace(BINANCE_SYMBOL_TO_ANCHORS, BinanceApi.SYMBOL_REPLACE_MAP).keys())

    @staticmethod
    def _build_query_id(symbol: Symbol, anchor: AnchorSymbol) -> QueryId:
        return "{}{}".format(symbol, anchor)

    @staticmethod
    def _get_query_ids(symbol: Symbol) -> List[QueryId]:
        if symbol == "USDT":
            return []
        else:
            anchors = BINANCE_SYMBOL_TO_ANCHORS[symbol]
            return [BinanceApi._build_query_id(symbol, anchor) for anchor in anchors]

    def _fetch_asset_status_by_symbols(self, symbols: List[Symbol]) -> List[QueriedData]:
        anchors = list()
        for symbol in symbols:
            anchors += BINANCE_SYMBOL_TO_ANCHORS[symbol]

        query_ids = []
        for symbol in symbols + anchors:
            query_ids += self._get_query_ids(symbol)

        query_ids = sorted(list(set(query_ids)))  # remove duplication
        api_url = "{}ticker/24hr".format(self.base_url)

        joined_query_id = "[%22" + "%22,%22".join(query_ids) + "%22]"
        return self._request(api_url, {"symbols": joined_query_id})

    @staticmethod
    def _parse_price_and_volume_from_queried_data(
        query_id: QueryId, queried_data: List[QueriedData]
    ) -> Tuple[Price, Volume]:
        for data in queried_data:
            if data["symbol"] == query_id:
                price, volume = data["lastPrice"], data["volume"]
                return EthAmount(price), EthAmount(volume)
        return EthAmount.zero(), EthAmount.zero()

    @staticmethod
    def _calc_price_and_volume_in_usd(symbol: Symbol, queried_data: List[QueriedData]) -> Tuple[Price, Volume]:
        if symbol == "USDT":
            return EthAmount("1.0", 18), EthAmount.zero()  # TODO usdt volume zero?

        else:
            prices, volumes = list(), list()
            for anchor in BINANCE_SYMBOL_TO_ANCHORS[symbol]:
                anchor_price, _ = BinanceApi._calc_price_and_volume_in_usd(anchor, queried_data)
                target_price, target_volume = BinanceApi._parse_price_and_volume_from_queried_data(
                    BinanceApi._build_query_id(symbol, anchor), queried_data)
                prices.append(target_price * anchor_price)
                volumes.append(target_volume * anchor_price)

            weighted_price = eth_amount_weighted_sum(prices, volumes)
            return weighted_price, eth_amount_sum(volumes)

    def fetch_prices_with_volumes(self, symbols: List[Symbol]) -> Dict[Symbol, PriceVolume]:
        pairs = self._fetch_asset_status_by_symbols(symbols)

        ret = {}
        for symbol in symbols:
            price, volume = self._calc_price_and_volume_in_usd(symbol, pairs)
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
        self.assertEqual(symbols, list(BINANCE_SYMBOL_TO_ANCHORS.keys()))

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
