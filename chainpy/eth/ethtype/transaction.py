from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union

from dataclasses_json import LetterCase, dataclass_json, config
from eth_account import Account
from eth_account._utils.transaction_utils import transaction_rpc_to_rlp_structure
from eth_account._utils.typed_transactions import access_list_sede_type
from eth_rlp import HashableRLP

import rlp
from rlp.sedes import (
    big_endian_int, binary, Binary
)

from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.dataclassmeta import EthHashBytesMeta, IntegerMeta, EthHexBytesMeta, EthAddrMeta
from chainpy.eth.ethtype.exceptions import EthTypeError
from chainpy.eth.ethtype.hexbytes import EthHashBytes, EthAddress, EthHexBytes
from chainpy.eth.ethtype.utils import is_hex, keccak_hash

# Type 2 transaction
dynamic_unsigned_transaction_fields = (
    ('chainId', big_endian_int),
    ('nonce', big_endian_int),
    ('maxPriorityFeePerGas', big_endian_int),
    ('maxFeePerGas', big_endian_int),
    ('gas', big_endian_int),
    ('to', Binary.fixed_length(20, allow_empty=True)),
    ('value', big_endian_int),
    ('data', binary),
    ('accessList', access_list_sede_type),
)

dynamic_unsigned_transaction_serializer = type(
    "_unsigned_transaction_serializer", (HashableRLP,), {
        "fields": dynamic_unsigned_transaction_fields,
    },
)

# Type 1 transaction
access_list_unsigned_transaction_fields = (
    ('chainId', big_endian_int),
    ('nonce', big_endian_int),
    ('gasPrice', big_endian_int),
    ('gas', big_endian_int),
    ('to', Binary.fixed_length(20, allow_empty=True)),
    ('value', big_endian_int),
    ('data', binary),
    ('accessList', access_list_sede_type),
)

access_list_unsigned_transaction_serializer = type(
    "_unsigned_transaction_serializer", (HashableRLP,), {
        "fields": access_list_unsigned_transaction_fields,
    },
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthTransaction:
    hash: Optional[EthHashBytes] = field(metadata=EthHashBytesMeta, default_factory=str)

    block_hash: Optional[EthHashBytes] = field(metadata=EthHashBytesMeta, default_factory=str)
    block_number: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    sender: Optional[EthAddress] = field(
        metadata=config(
            field_name="from",
            encoder=lambda value: value.hex(),
            decoder=lambda value: EthAddress(value)
        ),
        default_factory=str
    )
    gas: int = field(metadata=IntegerMeta, default_factory=int)
    gas_price: int = field(metadata=IntegerMeta, default_factory=int)

    input: EthHexBytes = field(metadata=EthHexBytesMeta, default_factory=str)
    nonce: int = field(metadata=IntegerMeta, default_factory=int)
    r: int = field(metadata=IntegerMeta, default_factory=int)
    s: int = field(metadata=IntegerMeta, default_factory=int)
    v: int = field(metadata=IntegerMeta, default_factory=int)
    transaction_index: int = field(metadata=IntegerMeta, default_factory=int)
    value: int = field(metadata=IntegerMeta, default_factory=int)
    to: Optional[EthAddress] = field(metadata=EthAddrMeta, default_factory=str)

    # optional depends on rpc versions
    creates: Optional[EthAddress] = field(metadata=EthAddrMeta, default_factory=str)
    type: Optional[int] = field(metadata=IntegerMeta, default_factory=int)

    # type 1 and 2 only
    chain_id: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    access_list: Optional[List[Dict[str, Any]]] = field(default_factory=list)

    max_fee_per_gas: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    max_priority_fee_per_gas: Optional[int] = field(metadata=IntegerMeta, default_factory=int)

    def __post_init__(self):
        if EthHashBytes.default() == self.block_hash:
            self.type = -1

        if self.max_priority_fee_per_gas * self.max_fee_per_gas != 0:
            self.type = 2
        else:
            self.type = 0

    @classmethod
    def init(cls,
             chain_id: int,
             to: EthAddress,
             value: EthAmount = EthAmount.zero(),
             data: EthHexBytes = None,
             sender: EthAddress = None) -> "EthTransaction":
        tx_dict = {
            "chainId": hex(chain_id),
            "to": to.hex().lower(),
            "value": value.int() if value is not None else 0
        }
        if data is not None:
            tx_dict["input"] = data.hex().lower()
        if sender is not None:
            tx_dict["sender"] = sender.hex().lower()
        return EthTransaction.from_dict(tx_dict)

    def type_negative_one_tx_exception(self):
        if self.type == -1:
            raise Exception("Type -1 transaction can not have any field")

    def set_nonce(self, nonce: int):
        self.type_negative_one_tx_exception()
        self.nonce = nonce
        return self

    def set_gas_limit(self, gas_limit: Union[int, str]):
        self.type_negative_one_tx_exception()
        self.gas = gas_limit if isinstance(gas_limit, int) else hex(gas_limit)
        return self

    def set_gas_price(self, gas_price: int):
        """ set fee parameters for type0 or type1 transaction """
        self.type_negative_one_tx_exception()
        if self.type == 0 or self.type == 2:
            self.type = 0
        elif self.type == 1:
            self.type = 1
        else:
            raise Exception("Invalid transaction type: {}".format(self.type))

        self.gas_price = gas_price
        return self

    def set_gas_prices(self, max_fee_per_gas: int, max_priority_fee_per_gas: int):
        """ set fee parameters for type2 """
        self.type_negative_one_tx_exception()
        self.type = 2
        self.max_fee_per_gas = max_fee_per_gas
        self.max_priority_fee_per_gas = max_priority_fee_per_gas
        return self

    def set_access_list(self, access_list: list):
        if access_list is None or not isinstance(access_list, list):
            raise Exception("access_list must be list type, but {}".format(type(access_list)))
        self.type_negative_one_tx_exception()
        self.type = max(self.type, 1)
        self.access_list = access_list
        return self

    def set_chain_id(self, chain_id: int):
        self.type_negative_one_tx_exception()
        self.chain_id = chain_id
        return self

    def sign_transaction(self, account: EthAccount) -> EthHexBytes:
        transaction = self.send_dict(encoded=True)
        signed_tx = Account.sign_transaction(transaction, hex(account.priv))
        return EthHexBytes(signed_tx.rawTransaction)

    def serialize(self) -> EthHexBytes:
        transaction = self.send_dict(encoded=True)

        # RPC-structured transaction to rlp-structured transaction
        rlp_structured_txn_without_sig_fields = transaction_rpc_to_rlp_structure(transaction)
        rlp_serializer = access_list_unsigned_transaction_serializer \
            if self.type == 1 else dynamic_unsigned_transaction_serializer

        serializable_obj = rlp_serializer.from_dict(rlp_structured_txn_without_sig_fields),  # type: ignore
        rlp_encoded = rlp.encode(serializable_obj)
        return EthHexBytes(rlp_encoded)

    def tx_hash(self) -> EthHashBytes:
        if self.hash is None:
            serialized_tx = self.serialize()
            return keccak_hash(serialized_tx)
        return self.hash

    def is_sendable(self) -> bool:
        if self.nonce is None or self.gas is None:
            return False

        if self.type < 2 and self.gas_price is None:
            return False

        if self.type == 2 and (self.max_fee_per_gas is None or self.max_priority_fee_per_gas is None):
            return False

        return True

    def call_dict(self, from_addr: EthAddress = None, encoded: bool = False):
        ret_dict = {"to": self.to.hex().lower() if not encoded else self.to.bytes()}

        if self.input is not None:
            ret_dict["data"] = self.input.hex().lower() if not encoded else self.input.bytes()

        sender = from_addr if self.sender is None else self.sender
        if sender is not None:
            ret_dict["from"] = sender.hex().lower() if not encoded else sender.bytes()

        if self.value is not None:
            ret_dict["value"] = hex(self.value) if not encoded else self.value

        if ret_dict.get("input") is None and ret_dict.get("value") is None:
            raise Exception("Wrong call dict")

        return ret_dict

    def send_dict(self, encoded: bool = False) -> dict:
        if self.gas is None or self.nonce is None or self.to is None:
            raise Exception("empty necessary property: gas, nonce and to")

        if (self.type == 0 or self.type == 1) and self.gas_price is None:
            raise Exception("empty gas_price")

        if (self.type == 1 or self.type == 2) and self.access_list is None:
            raise Exception("empty access_list")

        if self.type == 2 and (self.max_fee_per_gas is None or self.max_priority_fee_per_gas is None):
            raise Exception("empty max_fee_per_gas or max_priority_fee_per_gas")

        value = hex(self.value) if self.value is not None else "0x00"
        transaction = {
            "chainId": hex(self.chain_id) if not encoded else self.chain_id,
            "to": self.to.hex().lower() if not encoded else self.to.bytes(),
            "value": value if not encoded else self.value,
            "nonce": hex(self.nonce) if not encoded else self.nonce,
            "gas": hex(self.gas) if not encoded else self.gas,
            "data": self.input.hex().lower() if not encoded else self.input.bytes()
        }
        if self.type < 2:
            transaction["gasPrice"] = hex(self.gas_price) if not encoded else self.gas_price
        if self.type > 0:
            transaction["accessList"] = self.access_list
        if self.type == 2:
            transaction["maxFeePerGas"] = hex(self.max_fee_per_gas) if not encoded else self.max_fee_per_gas
            transaction["maxPriorityFeePerGas"] = hex(self.max_priority_fee_per_gas) \
                if not encoded else self.max_priority_fee_per_gas
        return transaction


def encode_transaction(tx: EthTransaction):
    if tx.type == -1:
        return tx.hash.hex()
    else:
        return tx.to_dict()


def decode_transaction(tx: Union[dict, str]):
    if isinstance(tx, str) and is_hex(tx):
        return EthTransaction.from_dict({"hash": tx})
    elif isinstance(tx, dict):
        return EthTransaction.from_dict(tx)
    else:
        raise EthTypeError(Optional[dict, str], type(tx))


EthTransactionListMeta = config(
    decoder=lambda values: [decode_transaction(value) for value in values],
    encoder=lambda values: [encode_transaction(value) for value in values]
)
