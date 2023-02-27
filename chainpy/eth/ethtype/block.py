from dataclasses import dataclass, field
from typing import List, Optional

from dataclasses_json import LetterCase, Exclude, dataclass_json, config

from chainpy.eth.ethtype.dataclassmeta import (
    IntegerMeta,
    EthHexBytesMeta,
    EthAddrMeta,
    EthHashBytesMeta,
    EthHashBytesListMeta
)
from chainpy.eth.ethtype.exceptions import EthTypeError
from chainpy.eth.ethtype.hexbytes import EthHexBytes, EthHashBytes, EthAddress
from chainpy.eth.ethtype.transaction import EthTransactionListMeta, EthTransaction
from chainpy.eth.ethtype.utils import is_hex


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthBlock:
    verbose: bool = field(init=False, metadata=config(exclude=Exclude.ALWAYS))
    type: int = field(init=False, metadata=config(exclude=Exclude.ALWAYS))

    difficulty: int = field(metadata=IntegerMeta)
    extra_data: EthHexBytes = field(metadata=EthHexBytesMeta)
    gas_limit: int = field(metadata=IntegerMeta)
    gas_used: int = field(metadata=IntegerMeta)
    hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    logs_bloom: EthHexBytes = field(metadata=EthHexBytesMeta)
    miner: EthAddress = field(metadata=EthAddrMeta)

    number: int = field(metadata=IntegerMeta)
    parent_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    receipts_root: EthHashBytes = field(metadata=EthHashBytesMeta)
    sha3_uncles: EthHashBytes = field(metadata=EthHashBytesMeta)
    size: int = field(metadata=IntegerMeta)
    state_root: EthHashBytes = field(metadata=EthHashBytesMeta)
    timestamp: int = field(metadata=IntegerMeta)
    total_difficulty: int = field(metadata=IntegerMeta)
    transactions_root: EthHashBytes = field(metadata=EthHashBytesMeta)
    transactions: List[EthTransaction] = field(metadata=EthTransactionListMeta)
    uncles: List[EthHashBytes] = field(metadata=EthHashBytesListMeta)

    # required except to bifrost network
    mix_hash: EthHashBytes = field(metadata=EthHashBytesMeta, default_factory=str)
    nonce: int = field(metadata=IntegerMeta, default_factory=int)

    # BaseFee was added by EIP - 1559 and is ignored in legacy headers.
    base_fee_per_gas: Optional[int] = field(metadata=IntegerMeta, default_factory=str)

    def __post_init__(self):
        self.verbose = check_transaction_verbosity(self.transactions)
        self.type = 0 if self.base_fee_per_gas is None else 2

    def serialize(self) -> EthHexBytes:
        # TODO impl.
        raise Exception("Not implemented yet")

    def block_hash(self) -> EthHashBytes:
        # TODO impl.
        raise Exception("Not implemented yet")


def check_transaction_verbosity(values: list):
    if len(values) == 0:
        return False

    criteria = values[0]
    if isinstance(criteria, EthTransaction):
        return criteria.block_hash != EthHashBytes.default()
    else:
        if isinstance(criteria, dict):
            return True
        elif isinstance(criteria, str) and is_hex(criteria):
            return False
        else:
            raise EthTypeError(Optional[dict, str], type(criteria))
