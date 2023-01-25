import copy
from typing import Union, Dict, List, Any


def to_upper_list(targets: Union[str, list]) -> list:
    targets = targets.split(",") if isinstance(targets, str) else targets
    symbols = [symbol.upper() for symbol in targets]
    return list(set(symbols))


def replace_symbols(symbols: List[str], _map: Dict[str, str]) -> List[str]:
    symbols_clone = copy.deepcopy(symbols)
    for key, value in _map.items():
        try:
            idx = symbols_clone.index(key)
            symbols_clone[idx] = _map[key]
        except ValueError as e:
            continue
    return list(set(symbols_clone))


def restore_replace(items: Dict[str, Any], _map: Dict[str, str]) -> Dict[str, Any]:
    items_clone = copy.deepcopy(items)

    reversed_dict = {}
    for key, value in _map.items():
        reversed_dict[value] = key

    for key, value in reversed_dict.items():
        value = items_clone.get(key)
        if value is not None:
            del items_clone[key]
            items_clone[reversed_dict[key]] = value
    return items_clone
