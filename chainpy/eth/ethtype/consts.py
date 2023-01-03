from enum import Enum
from typing import List


class EnumInterface(Enum):
    @classmethod
    def from_name(cls, name):
        return cls.__dict__[name]

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

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
    NONE         = 0x00000000
    BITCOIN      = 0x01000001
    BITCOIN_CASH = 0x01000002

    # ETHEREUM-like chains
    BIFROST      = 0x02000003
    ETHEREUM     = 0x02000004
    BINANCE      = 0x02000005
    AVALANCHE    = 0x02000006
    KLAYTN       = 0x02000007
    POLYGON      = 0x02000008

    # for oracle
    RESERVED_01  = 0x00000001
    RESERVED_02  = 0x00000002
    RESERVED_03  = 0x00000003
    RESERVED_04  = 0x00000004
    RESERVED_05  = 0x00000005

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []

    @staticmethod
    def size():
        return 4
