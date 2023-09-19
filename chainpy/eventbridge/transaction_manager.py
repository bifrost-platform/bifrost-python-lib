import queue
import time
from typing import Union

from eth_keys.datatypes import PrivateKey
from eth_typing import HexStr
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.middleware import construct_sign_and_send_raw_middleware
from web3.types import TxData


class TransactionManager:
    def __init__(self, url: str, chain_name: str, block_period_sec: int, private_key: Union[None, PrivateKey] = None):
        self.chain_name = chain_name

        self.w3 = Web3(Web3.HTTPProvider(url))
        if private_key is not None:
            self.w3.middleware_onion.add(construct_sign_and_send_raw_middleware(private_key))

        self.block_period_sec = block_period_sec

        self.queue = queue.PriorityQueue()

    def set_signer(self, private_key: PrivateKey):
        self.w3.middleware_onion.add(construct_sign_and_send_raw_middleware(private_key_or_account=private_key))

    def enqueue(self, tx_hash: HexStr):
        if tx_hash is None:
            return
        else:
            for i in range(0, 5):
                try:
                    nonce = self.w3.eth.get_transaction(tx_hash)['nonce']
                    self.queue.put((nonce, tx_hash))
                    break
                except TransactionNotFound:
                    time.sleep(1)
                    continue
            return

    def run_transaction_manager(self):
        while True:
            while self.queue.not_empty:
                pending: (int, HexStr) = self.queue.get()

                for i in range(0, 5):
                    try:
                        transaction: TxData = self.w3.eth.get_transaction(transaction_hash=pending[1])
                        if transaction['blockHash'] is None:
                            new_tx_hash = self.w3.eth.replace_transaction(transaction_hash=pending[1], new_transaction={
                                'to': transaction['to'],
                                'from': transaction['from'],
                                'value': transaction['value'],
                                'data': transaction['input'],
                                'gas': transaction['gas']
                            })
                            self.queue.put((pending[0], HexStr(new_tx_hash.hex())))

                    except TransactionNotFound:
                        raise Exception(f"Undone action lost in txpool. tx_hash: {pending[1]}")

                self.queue.task_done()

            time.sleep(self.block_period_sec)
