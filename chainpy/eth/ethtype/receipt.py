from dataclasses import dataclass, field
from typing import Optional, List

from dataclasses_json import dataclass_json, LetterCase, config

from .dataclassmeta import IntegerMeta, EthHexBytesMeta, EthHashBytesMeta, EthAddrMeta, EthHashBytesListMeta
from .hexbytes import EthHashBytes, EthAddress, EthHexBytes


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthLog:
    # log has single type
    address: EthAddress = field(metadata=EthAddrMeta)
    block_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    block_number: int = field(metadata=IntegerMeta)
    data: EthHexBytes = field(metadata=EthHexBytesMeta)
    log_index: int = field(metadata=IntegerMeta)
    removed: bool
    topics: List[EthHashBytes] = field(metadata=EthHashBytesListMeta)
    transaction_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    transaction_index: int = field(metadata=IntegerMeta)


EthLogListMeta = config(
    decoder=lambda values: [EthLog.from_dict(value) for value in values],
    encoder=lambda values: [value.to_dict() for value in values]
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthReceipt:
    # receipt has single type
    block_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    block_number: int = field(metadata=IntegerMeta)

    cumulative_gas_used: int = field(metadata=IntegerMeta)
    effective_gas_price: int = field(metadata=IntegerMeta)
    sender: EthAddress = field(
        metadata=config(
            field_name="from",
            encoder=lambda value: value.hex(),
            decoder=lambda value: EthAddress(value)
        )
    )
    gas_used: int = field(metadata=IntegerMeta)
    logs: List[EthLog] = field(metadata=EthLogListMeta)
    logs_bloom: EthHexBytes = field(metadata=EthHexBytesMeta)
    status: int = field(metadata=IntegerMeta)
    to: EthAddress = field(metadata=EthAddrMeta)
    transaction_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    transaction_index: int = field(metadata=IntegerMeta)

    type: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    contract_address: Optional[EthAddress] = field(metadata=EthAddrMeta, default_factory=str)

    def __post_init__(self):
        if self.type is None:
            self.type = 0

    def get_log_data_by_topic(self, topic: EthHashBytes) -> Optional[EthHexBytes]:
        for log in self.logs:
            for topic_in_log in log.topics:
                if topic == topic_in_log:
                    return log.data
        return None
