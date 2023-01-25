import unittest
from typing import List, Tuple

from .priceapiabc import PriceApiABC, QueriedData, Symbol, QueryId, Price, Volume, AnchorSymbol
from chainpy.offchain.consts.upbitconst import UPBIT_SYMBOL_TO_ANCHORS
from .utils import restore_replace
from ..eth.ethtype.amount import EthAmount, eth_amount_weighted_sum, eth_amount_sum

"""
Upbit open api: https://docs.upbit.com/reference/

- supporting market information
    - https://docs.upbit.com/reference/%EB%A7%88%EC%BC%93-%EC%BD%94%EB%93%9C-%EC%A1%B0%ED%9A%8C
"""


class UpbitApi(PriceApiABC):
    ANCHOR_SYMBOLS = ["USDT", "BTC", "KRW"]
    SYMBOL_REPLACE_MAP = {}

    def __init__(self, api_base_url: str, request_timeout_sec: int = 300):
        super().__init__(api_base_url, request_timeout_sec=request_timeout_sec)

    def ping(self) -> bool:
        result = self.get_current_prices_with_volumes("BTC")
        return "BTC" in result.keys() \
               and isinstance(result["BTC"].price(), EthAmount) \
               and isinstance(result["BTC"].volume(), EthAmount)

    @staticmethod
    def is_anchor(symbol: Symbol) -> bool:
        return symbol in UpbitApi.ANCHOR_SYMBOLS

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(restore_replace(UPBIT_SYMBOL_TO_ANCHORS, UpbitApi.SYMBOL_REPLACE_MAP).keys())

    @staticmethod
    def _build_query_id(symbol: Symbol, anchor: AnchorSymbol) -> QueryId:
        return "{}-{}".format(anchor, symbol)

    @staticmethod
    def _get_query_ids(symbol: Symbol) -> List[QueryId]:
        if symbol == "USDT":
            return []
        elif symbol == "KRW":
            return ["USDT-BTC", "KRW-BTC"]
        else:
            anchors = UPBIT_SYMBOL_TO_ANCHORS[symbol]
            return [UpbitApi._build_query_id(symbol, anchor) for anchor in anchors]

    def _fetch_asset_status_by_symbols(self, symbols: List[Symbol]) -> List[QueriedData]:
        anchors = list()
        for symbol in symbols:
            anchors += UPBIT_SYMBOL_TO_ANCHORS[symbol]

        query_ids = []
        for symbol in symbols + anchors:
            query_ids += self._get_query_ids(symbol)

        query_ids = sorted(list(set(query_ids)))  # remove duplication
        query_str = ",".join(query_ids)
        if query_str == "":
            return list(dict())

        api_url = "{}ticker".format(self.base_url)
        return self._request(api_url, {"markets": query_str})

    @staticmethod
    def _parse_price_and_volume_from_queried_data(
            query_id: QueryId, queried_data: List[QueriedData]
    ) -> Tuple[Price, Volume]:
        for data in queried_data:
            if data["market"] == query_id:
                price, volume = data["trade_price"], data["acc_trade_price_24h"]
                if isinstance(price, int):
                    price = float(price)
                if isinstance(volume, int):
                    volume = float(volume)
                return EthAmount(price), EthAmount(volume)
        return EthAmount.zero(), EthAmount.zero()

    @staticmethod
    def _calc_price_and_volume_in_usd(symbol: Symbol, queried_data: List[QueriedData]) -> Tuple[Price, Volume]:
        if symbol == "USDT":
            return EthAmount("1.0", 18), EthAmount.zero()  # TODO usdt volume zero?

        if symbol == "KRW":
            btc_price_in_usd, _ = UpbitApi._parse_price_and_volume_from_queried_data("USDT-BTC", queried_data)
            btc_price_in_krw, _ = UpbitApi._parse_price_and_volume_from_queried_data("KRW-BTC", queried_data)
            return btc_price_in_usd / btc_price_in_krw, EthAmount.zero()

        else:
            market_prices, market_volumes = list(), list()
            for anchor in UPBIT_SYMBOL_TO_ANCHORS[symbol]:
                anchor_price, _ = UpbitApi._calc_price_and_volume_in_usd(anchor, queried_data)
                target_price, target_volume = UpbitApi._parse_price_and_volume_from_queried_data(
                    UpbitApi._build_query_id(symbol, anchor), queried_data)
                market_prices.append(target_price * anchor_price)
                market_volumes.append(target_volume * anchor_price)

            weighted_price = eth_amount_weighted_sum(market_prices, market_volumes)
            return weighted_price, eth_amount_sum(market_volumes)


class TestUpbitApi(unittest.TestCase):
    def setUp(self) -> None:
        # Open api url
        self.api = UpbitApi("https://api.upbit.com/v1/")

        # Currently, The Upbit does not provide prices of BNB, USDC, BIFI
        self.symbols = ["ETH", "MATIC", "BFC", "USDT"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_supporting_symbol(self):
        symbols = self.api.supported_symbols()
        self.assertEqual(type(symbols), list)
        self.assertEqual(symbols, list(UPBIT_SYMBOL_TO_ANCHORS.keys()))

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
