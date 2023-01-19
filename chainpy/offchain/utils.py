import json
from typing import Union, Dict


def to_list(targets: Union[str, list]) -> list:
    targets = targets.split(",") if isinstance(targets, str) else targets
    return list(set(targets))
