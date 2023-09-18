from dataclasses import dataclass
from typing import List, Optional, Union

from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class FeeConfig:
    type: int
    gas_price: Optional[int] = None
    max_gas_price: Optional[int] = None
    max_priority_price: Optional[int] = None
    fee_update_rates: Optional[List[float]] = None

    def __post_init__(self):
        if self.type != 0 and self.type != 2:
            raise Exception("Not supported transaction type: {}".format(self.type))
        if self.type == 0:
            if self.gas_price is None:
                raise Exception("Type0 fee config Must have gas_price")
        if self.type == 2:
            if self.max_gas_price is None or self.max_priority_price is None:
                raise Exception("Type2 fee config Must have max_gas_price and max_priority_price")

        if self.fee_update_rates is None:
            self.fee_update_rates = [1.1, 1.2, 1.3, 2]


def merge_dict(base_dict: dict, add_dict: dict):
    if add_dict is None:
        return base_dict
    if not isinstance(add_dict, dict):
        return add_dict

    for key, value in add_dict.items():
        if base_dict.get(key) is None:
            base_dict[key] = {}
        base_dict[key] = merge_dict(base_dict[key], add_dict[key])
    return base_dict


def hex_height_or_latest(height: Union[int, str] = "latest") -> str:
    if height in ["latest", "earliest", "pending", "safe", "finalized"]:
        return height
    if isinstance(height, int):
        return hex(height)
    raise Exception("height should be integer or \"latest\"")
