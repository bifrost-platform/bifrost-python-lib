import json
from abc import ABCMeta, abstractmethod
from typing import List, Union, Dict, Tuple

import requests

from .utils import to_upper_list, replace_symbols, restore_replace
from ..eth.ethtype.amount import EthAmount, eth_amount_weighted_sum, eth_amount_avg

Symbol, AnchorSymbol, QueryId, QueriedData = str, str, str, dict
Price, Volume, Symbol2Price = EthAmount, EthAmount, Dict[Symbol, EthAmount]


class PriceVolume:
    def __init__(self, symbol: Symbol, price: Price, volume: Volume = None):
        self._symbol = symbol
        self._price = price.change_decimal(18)
        self._volume = volume if volume is not None else EthAmount.zero()

    @classmethod
    def init(cls, symbol: Symbol):
        return cls(symbol, EthAmount.zero(), EthAmount.zero())

    def append(self, price: Price, volume: Volume):
        self._price = eth_amount_weighted_sum([self._price, price.change_decimal(18)], [self._volume, volume])
        self._volume += volume

    def release(self) -> Tuple[Price, Volume]:
        return self._price, self._volume

    def price(self) -> Price:
        return self._price

    def volume(self) -> Volume:
        return self._volume

    def symbol(self) -> Symbol:
        return self._symbol


class PricesVolumes:
    def __init__(self, symbol: Symbol, prices: List[Price], volumes: List[Volume]):
        self._symbol = symbol
        self._prices = prices
        self._volumes = volumes

    @classmethod
    def init(cls, symbol: Symbol):
        return cls(symbol, [], [])

    def append(self, price: Price, volume: Volume):
        self._prices.append(price.change_decimal(18))
        self._volumes.append(volume)

    def averaged_price(self) -> Price:
        if len(self._prices) == 0:
            raise Exception("No price: {}".format(self._symbol))
        return eth_amount_avg(self._prices)

    def volume_weighted_price(self) -> Price:
        return eth_amount_weighted_sum(self._prices, self._volumes)


class PriceApiABC(metaclass=ABCMeta):
    SYMBOL_REPLACE_MAP = {}

    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        self._api_base_url = api_base_url
        self._request_timeout_sec = request_timeout_sec

    def _request(self, api_url: str, params: dict = None, api_url_has_params=False):
        if params:
            api_url += '&' if api_url_has_params else '?'
            for key, value in params.items():
                if type(value) == bool:
                    value = str(value).lower()

                api_url += "{0}={1}&".format(key, str(value))
            api_url = api_url[:-1]

        result = requests.get(api_url, timeout=self._request_timeout_sec)
        result.raise_for_status()
        return json.loads(result.content.decode("utf-8"))

    @property
    def base_url(self) -> str:
        return self._api_base_url

    def check_supported(self, symbols: List[Symbol]) -> List[Symbol]:
        supported_symbols = self.supported_symbols()

        supported_subset = list()
        for symbol in symbols:
            if symbol in supported_symbols:
                supported_subset.append(symbol)

        return supported_subset

    @abstractmethod
    def ping(self) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def supported_symbols() -> List[Symbol]:
        pass

    @abstractmethod
    def _fetch_asset_status_by_symbols(self, symbols: List[Symbol]) -> List[QueriedData]:
        pass

    @staticmethod
    @abstractmethod
    def _parse_price_and_volume_from_queried_data(query_id: QueryId, markets: List[QueriedData]) -> Tuple[Price, Volume]:
        pass

    @staticmethod
    @abstractmethod
    def _calc_price_and_volume_in_usd(symbol: Symbol, markets: List[QueriedData]) -> Tuple[Price, Volume]:
        pass

    def fetch_prices_with_volumes(self, symbols: List[Symbol]) -> Dict[Symbol, PriceVolume]:
        queried_data = self._fetch_asset_status_by_symbols(symbols)

        ret = {}
        for symbol in symbols:
            price, volume = self._calc_price_and_volume_in_usd(symbol, queried_data)
            if ret.get(symbol) is not None:
                ret[symbol].append(price, volume)
            else:
                ret[symbol] = PriceVolume(symbol, price, volume)
        return ret

    def get_current_prices_with_volumes(
        self, symbols: Union[Symbol, List[Symbol]]
    ) -> Dict[Symbol, PriceVolume]:
        symbols = to_upper_list(symbols)
        supported_subset = self.check_supported(symbols)
        if symbols != supported_subset:
            raise Exception("Not supported symbols: {}".format(set(symbols).difference(supported_subset)))

        symbols = replace_symbols(symbols, self.__class__.SYMBOL_REPLACE_MAP)

        pvs = self.fetch_prices_with_volumes(symbols)

        return restore_replace(pvs, self.__class__.SYMBOL_REPLACE_MAP)

    def get_current_prices(
        self, symbols: Union[List[Symbol], Symbol]
    ) -> Dict[Symbol, Price]:
        results = self.get_current_prices_with_volumes(symbols)
        ret = dict()
        for symbol, pv in results.items():
            ret[symbol] = pv.price()
        return ret
