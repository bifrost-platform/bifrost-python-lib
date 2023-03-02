import copy


def change_block_verbosity(block: dict) -> dict:
    block_clone = copy.deepcopy(block)

    transactions = block_clone["transactions"]
    if len(transactions) == 0 or isinstance(transactions[0], str):
        return block_clone
    else:
        tx_hash_list = list()
        for tx_dict in transactions:
            tx_hash_list.append(tx_dict["hash"])
        block_clone["transactions"] = tx_hash_list
        return block_clone
