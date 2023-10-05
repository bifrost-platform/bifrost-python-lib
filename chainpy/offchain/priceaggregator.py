from enum import Enum
from typing import List, Union, Dict, Optional, Callable

from .binanceapi import BinanceApi
from .chainlinkapi import ChainlinkApi
from .coingeckoapi import CoingeckoApi
from .gateioapi import GateIoApi
from .priceapiabc import PriceApiABC, Symbol, Symbol2Price, PricesVolumes
from .upbitapi import UpbitApi
from .utils import to_upper_list
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
