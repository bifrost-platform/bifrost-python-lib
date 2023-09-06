import os
import unittest
from enum import Enum
from typing import List, Union, Dict, Optional, Callable

from dotenv import load_dotenv

from chainpy.offchain.consts.chainlinkconst import ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS
from chainpy.offchain.consts.coingeckoconst import COINGECKO_SYMBOL_TO_QUERY_ID
from chainpy.offchain.consts.upbitconst import UPBIT_SYMBOL_TO_ANCHORS
from .binanceapi import BinanceApi
from .chainlinkapi import ChainlinkApi
from .coingeckoapi import CoingeckoApi
from .consts.binanceconst import BINANCE_SYMBOL_TO_ANCHORS
from .consts.gateioconst import GATE_IO_SYMBOL_TO_ANCHORS
from .gateioapi import GateIoApi
from .priceapiabc import PriceApiABC, Symbol, Symbol2Price, PricesVolumes
from .upbitapi import UpbitApi
from .utils import to_upper_list, restore_replace
from ..eth.ethtype.amount import EthAmount
from ..logger import global_logger


class PriceApiIdx(Enum):
    COINGECKO = 1
    UPBIT = 2
    CHAINLINK = 3
    BINANCE = 4
    GATEIO = 5

    @staticmethod
    def from_name(name: str) -> Optional["PriceApiIdx"]:
        for idx in PriceApiIdx:
            if idx.name == name.upper():
                return idx
        return None

    @staticmethod
    def api_selector(src_name: str) -> Callable:
        normalized_name = src_name.capitalize()
        if normalized_name == "Coingecko":
            return CoingeckoApi
        if normalized_name == "Upbit":
            return UpbitApi
        if normalized_name == "Chainlink":
            return ChainlinkApi
        if normalized_name == "Binance":
            return BinanceApi
        if normalized_name == "Gateio":
            return GateIoApi

        raise Exception("Not supported api name: {}".format(src_name))


class PriceOracleAgg:
    def __init__(self, urls: dict):
        self.apis: Dict[PriceApiIdx, PriceApiABC] = dict()
        for name in urls.keys():
            src_index = PriceApiIdx.from_name(name)
            api = PriceApiIdx.api_selector(name)
            self.apis[src_index] = api(urls[name])

        self.__supported_symbols_each: Dict[PriceApiIdx, List[Symbol]] = {}
        self.__supported_symbol_union: List[Symbol] = []
        for idx, api in self.apis.items():
            supported_symbols = api.supported_symbols()
            self.__supported_symbols_each[idx] = supported_symbols
            self.__supported_symbol_union += supported_symbols
        self.__supported_symbol_union = list(set(self.__supported_symbol_union))

    def ping(self) -> bool:
        for api in self.apis.values():
            if not api.ping():
                return False
        return True

    @property
    def supported_api_indices(self) -> List[PriceApiIdx]:
        return list(self.apis.keys())

    @property
    def supported_apis(self) -> List[PriceApiABC]:
        return list(self.apis.values())

    @property
    def supported_symbols(self) -> List[Symbol]:
        return self.__supported_symbol_union

    @property
    def supported_symbols_each(self) -> Dict[PriceApiIdx, List[Symbol]]:
        return self.__supported_symbols_each

    def get_apis_supporting_symbol(self, symbol: Symbol) -> List[PriceApiIdx]:
        apis = list()
        for idx, symbols in self.supported_symbols_each.items():
            if symbol in symbols:
                apis.append(idx)
        return apis

    def fetch_prices_and_volumes(self, symbols: Union[Symbol, List[Symbol]]) -> Dict[Symbol, PricesVolumes]:
        # ensure symbols is list
        symbols = to_upper_list(symbols)
        symbols = [symbol.upper() for symbol in symbols]

        # ensure every symbol are supported
        for symbol in symbols:
            if symbol not in self.supported_symbols:
                raise Exception("Not allowed token symbol({}), select tokens in {}".format(
                    symbol,
                    self.supported_symbols
                ))

        # Symbols supported by each api
        api_to_symbols_map: Dict[PriceApiIdx, List[Symbol]] = {}
        for api_idx, api in self.apis.items():
            api_to_symbols_map[api_idx] = list(set(api.supported_symbols()).intersection(symbols))

        # pv: price and _volumes
        symbol_to_prices_volumes: Dict[Symbol, PricesVolumes] = dict()
        for symbol in symbols:
            symbol_to_prices_volumes[symbol] = PricesVolumes.init(symbol)

        for api_idx, supporting_symbols in api_to_symbols_map.items():
            try:
                symbol_to_pv_from_api = self.apis[api_idx].get_current_prices_with_volumes(supporting_symbols)
            except Exception as e:
                # TODO log
                global_logger.formatted_log(
                    "PriceAPI",
                    msg="{}\n  - msg: {}".format(api_idx.name, e)
                )
                continue

            for symbol, pv in symbol_to_pv_from_api.items():
                symbol_to_prices_volumes[symbol].append(pv.price(), pv.volume())

        return symbol_to_prices_volumes

    def get_current_averaged_price(self, symbols: Union[Symbol, List[Symbol]]) -> Symbol2Price:
        symbol_to_pv_list = self.fetch_prices_and_volumes(symbols)

        symbol_to_price: Symbol2Price = {}
        for symbol in symbols:
            symbol_to_price[symbol] = symbol_to_pv_list[symbol].averaged_price()
        return symbol_to_price

    def get_current_weighted_price(self, symbols: Union[Symbol, List[Symbol]]) -> Symbol2Price:
        symbol_to_pv_list = self.fetch_prices_and_volumes(symbols)

        symbol_to_price: Dict[Symbol, EthAmount] = {}
        for symbol in symbols:
            symbol_to_price[symbol] = symbol_to_pv_list[symbol].volume_weighted_price()
        return symbol_to_price


class TestPriceAggregator(unittest.TestCase):
    def setUp(self) -> None:
        load_dotenv()

        urls = {
            "Coingecko": "https://api.coingecko.com/api/v3/",
            "Upbit": "https://api.upbit.com/v1/",
            "Chainlink": os.environ.get("ETHEREUM_MAINNET_ENDPOINT"),
            "Binance": "https://api.binance.com/api/v3/",
            "GateIo": "https://api.gateio.ws/api/v4/"
        }
        self.agg = PriceOracleAgg(urls)
        self.symbols = ["BFC", "ETH", "BNB", "MATIC", "USDC", "BIFI"]

    def test_ping(self):
        result = self.agg.ping()
        self.assertTrue(result)

    def test_supporting_symbol(self):
        coingecko_supports = list(restore_replace(COINGECKO_SYMBOL_TO_QUERY_ID, CoingeckoApi.SYMBOL_REPLACE_MAP).keys())
        upbit_supports = list(restore_replace(UPBIT_SYMBOL_TO_ANCHORS, UpbitApi.SYMBOL_REPLACE_MAP).keys())
        chainlink_supports = list(
            restore_replace(ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS, ChainlinkApi.SYMBOL_REPLACE_MAP).keys())
        binance_supports = list(restore_replace(BINANCE_SYMBOL_TO_ANCHORS, BinanceApi.SYMBOL_REPLACE_MAP).keys())
        gate_io_supports = list(restore_replace(GATE_IO_SYMBOL_TO_ANCHORS, GateIoApi.SYMBOL_REPLACE_MAP).keys())
        expected_supports = sorted(list(set(
            coingecko_supports + upbit_supports + chainlink_supports + binance_supports + gate_io_supports
        )))

        actual_supported_symbols = sorted(self.agg.supported_symbols)
        self.assertEqual(type(actual_supported_symbols), list)
        self.assertEqual(actual_supported_symbols, expected_supports)

    def test_fetch_prices_and_volumes(self):
        results = self.agg.fetch_prices_and_volumes(self.symbols)
        for symbol, pv_list in results.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(pv_list, PricesVolumes))

    def test_get_current_averaged_price(self):
        results = self.agg.get_current_averaged_price(self.symbols)
        for symbol, price in results.items():
            self.assertTrue(isinstance(symbol, Symbol))
            self.assertTrue(isinstance(price, EthAmount))
            self.assertNotEqual(price, EthAmount.zero())

    def test_get_current_weighted_price(self):
        results = self.agg.get_current_weighted_price(self.symbols)
        for symbol, price in results.items():
            self.assertTrue(isinstance(symbol, Symbol))
            self.assertTrue(isinstance(price, EthAmount))
            if price == EthAmount.zero():
                raise Exception("zero price: {}".format(symbol))
            self.assertNotEqual(price, EthAmount.zero())
