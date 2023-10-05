from typing import List, Tuple

from chainpy.offchain.consts.chainlinkconst import ETH_CHAINLINK_SYMBOL_TO_CONTRACT_ADDRESS
from .priceapiabc import PriceApiABC, Symbol, QueryId, QueriedData, Price, Volume
from .utils import restore_replace
from ..eth.ethtype.amount import EthAmount
from ..eth.managers.rpchandler import EthRpcClient


class ChainlinkApi(PriceApiABC):
    SYMBOL_REPLACE_MAP = {}

    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

        chain_config = {"chain_name": "ETH_MAIN", "block_period_sec": 13, "url_with_access_key": api_base_url}
        self.__rpc_cli = EthRpcClient.from_config_dict(chain_config)

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
