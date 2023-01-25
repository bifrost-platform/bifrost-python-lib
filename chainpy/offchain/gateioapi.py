import unittest
from typing import Tuple, List

from chainpy.eth.ethtype.amount import EthAmount, eth_amount_weighted_sum, eth_amount_sum
from chainpy.offchain.consts.gateioconst import GATE_IO_SYMBOL_TO_ANCHORS
from chainpy.offchain.priceapiabc import PriceApiABC, Symbol, QueriedData, QueryId, AnchorSymbol, Price, Volume
from chainpy.offchain.utils import restore_replace, replace_symbols


class GateIoApi(PriceApiABC):
    ANCHOR_SYMBOLS = ["ETH", "USDT", "BTC"]
    SYMBOL_REPLACE_MAP = {
        "BIFI": "BIFIF"
    }

    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

    def ping(self) -> bool:
        api_url = "{}spot/tickers".format(self.base_url)
        result = self._request(api_url, params={"currency_pair": "BTC_USDT"})
        if not isinstance(result, list) or len(result) <= 0:
            return False
        elif result[0].get("currency_pair") is None:
            return False
        else:
            return True

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(restore_replace(GATE_IO_SYMBOL_TO_ANCHORS, GateIoApi.SYMBOL_REPLACE_MAP).keys())

    @staticmethod
    def _build_query_id(symbol: Symbol, anchor: AnchorSymbol):
        return "{}_{}".format(symbol, anchor)

    @staticmethod
    def _get_query_ids(symbol: Symbol) -> List[QueryId]:
        if symbol == "USDT":
            return []
        else:
            anchors = GATE_IO_SYMBOL_TO_ANCHORS[symbol]
            return [GateIoApi._build_query_id(symbol, anchor) for anchor in anchors]

    def _fetch_asset_status_by_symbols(self, symbols: List[Symbol]) -> List[QueriedData]:
        symbols = replace_symbols(symbols, self.__class__.SYMBOL_REPLACE_MAP)

        anchors = list()
        for symbol in symbols:
            anchors += GATE_IO_SYMBOL_TO_ANCHORS[symbol]

        query_ids = []
        for symbol in symbols + anchors:
            query_ids += self._get_query_ids(symbol)

        query_ids = sorted(list(set(query_ids)))  # remove duplication

        api_url = "{}spot/tickers".format(self.base_url)
        queried_data = self._request(api_url)

        ret_queried_data = list()
        for data in queried_data:
            if data["currency_pair"] in query_ids:
                ret_queried_data.append(data)
        return ret_queried_data

    @staticmethod
    def _calc_price_and_volume_in_usd(symbol: Symbol, queried_data: List[QueriedData]) -> Tuple[Price, Volume]:
        if symbol == "USDT":
            return EthAmount("1.0", 18), EthAmount.zero()  # TODO usdt volume zero?

        else:
            market_prices, market_volumes = list(), list()
            for anchor in GATE_IO_SYMBOL_TO_ANCHORS[symbol]:
                anchor_price, _ = GateIoApi._calc_price_and_volume_in_usd(anchor, queried_data)
                target_price, target_volume = GateIoApi._parse_price_and_volume_from_queried_data(
                    GateIoApi._build_query_id(symbol, anchor), queried_data)
                market_prices.append(target_price * anchor_price)
                market_volumes.append(target_volume * anchor_price)

            weighted_price = eth_amount_weighted_sum(market_prices, market_volumes)
            return weighted_price, eth_amount_sum(market_volumes)

    @staticmethod
    def _parse_price_and_volume_from_queried_data(
            query_id: QueryId, queried_data: List[QueriedData]
    ) -> Tuple[Price, Volume]:
        for data in queried_data:
            if data["currency_pair"] == query_id:
                price, volume = data["last"], data["quote_volume"]
                if isinstance(price, int):
                    price = float(price)
                if isinstance(volume, int):
                    volume = float(volume)
                return EthAmount(price), EthAmount(volume) * 2
        return EthAmount.zero(), EthAmount.zero()


class TestGateIoApi(unittest.TestCase):
    def setUp(self) -> None:
        self.api = GateIoApi("https://api.gateio.ws/api/v4/")
        # GateIo does not support USDC
        self.symbols = ["BFC", "ETH", "BNB", "MATIC", "BIFI"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_supporting_symbol(self):
        symbols = self.api.supported_symbols()
        expected_supporting_symbols = list(
            restore_replace(GATE_IO_SYMBOL_TO_ANCHORS, GateIoApi.SYMBOL_REPLACE_MAP).keys()
        )
        self.assertEqual(type(symbols), list)
        self.assertEqual(symbols, expected_supporting_symbols)

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
            print("symbol: {}, price: {}".format(symbol, price))
