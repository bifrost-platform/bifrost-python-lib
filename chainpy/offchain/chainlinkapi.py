import os
import unittest
from typing import List, Tuple

from dotenv import load_dotenv

from chainpy.offchain.consts.chainlinkconst import ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS
from .priceapiabc import PriceApiABC, Symbol, QueryId, QueriedData, Price, Volume
from .utils import restore_replace
from ..eth.managers.rpchandler import EthRpcClient
from ..eth.ethtype.amount import EthAmount
from bridgeconst.consts import Chain


class ChainlinkApi(PriceApiABC):
    SYMBOL_REPLACE_MAP = {}

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
        return list(restore_replace(ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS, ChainlinkApi.SYMBOL_REPLACE_MAP).keys())

    @staticmethod
    def _get_contract_address(symbol: Symbol) -> QueryId:
        return ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS[symbol]

    def _fetch_asset_status_by_symbols(self, symbols: List[Symbol]) -> List[QueriedData]:
        queried_data: List[QueriedData] = list()
        for symbol in symbols:
            contract_address = ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS[symbol]
            if contract_address == "0x0000000000000000000000000000000000000000":
                raise Exception("Not supported symbol (zero address): {}".format(symbol))
            result = self.__rpc_cli.eth_call({"to": contract_address, "data": "0xfeaf968c"})
            queried_data.append({"symbol": symbol, "data": result})
        return queried_data

    @staticmethod
    def _parse_price_and_volume_from_queried_data(
            query_id: QueryId, queried_data: List[QueriedData]
    ) -> Tuple[Price, Volume]:
        for data in queried_data:
            if data["symbol"] == query_id:
                price = EthAmount(int.from_bytes(data["data"][32:64], byteorder="big"), 8)
                volume = EthAmount.zero()
                return price, volume
        return EthAmount.zero(), EthAmount.zero()

    @staticmethod
    def _calc_price_and_volume_in_usd(symbol: Symbol, queried_data: List[QueriedData]) -> Tuple[Price, Volume]:
        return ChainlinkApi._parse_price_and_volume_from_queried_data(symbol, queried_data)


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
        self.assertEqual(symbols, list(ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS.keys()))

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
