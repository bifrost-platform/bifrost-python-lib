from enum import Enum
from typing import List


class EnumInterface(Enum):
    @classmethod
    def from_name(cls, name):
        return cls.__dict__[name]

    @classmethod
    def str_with_size(cls):
        return cls.__name__ + "-{}".format(cls.size())

    @staticmethod
    def is_composed() -> bool:
        raise Exception("Not implemented")

    @staticmethod
    def components() -> List[str]:
        raise Exception("Not implemented")

    @staticmethod
    def size() -> int:
        raise Exception("Not implemented")

    def formatted_bytes(self) -> bytes:
        return self.value.to_bytes(self.size(), "big")

    def formatted_hex(self) -> str:
        return "0x" + self.formatted_bytes().hex()


class Chain(EnumInterface):
    # BITCOIN-like chains
    NONE = 0
    BTC_MAIN = 536887296  # version of header
    BTC_TEST = 536870912  # version of header

    # ETHEREUM-like chains
    BFC_MAIN = 0x0bfc
    BFC_TEST = 0xbfc0

    ETH_MAIN = 1
    ETH_GOERLI = 5
    ETH_SEPOLIA = 11155111

    BNB_MAIN = 56
    BNB_TEST = 97
    AVAX_MAIN = 43114
    AVAX_FUJI = 43113
    KLAY_MAIN = 8217
    KLAY_TEST = 1001
    MATIC_MAIN = 137
    MATIC_MUMBAI = 80001

    # for oracle
    RESERVED_01  = 0xffffffff
    RESERVED_02  = 0xfffffffe
    RESERVED_03  = 0xfffffffd
    RESERVED_04  = 0xfffffffc
    RESERVED_05  = 0xfffffffb

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []

    @staticmethod
    def size():
        return 4
