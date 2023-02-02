import os
import sys
import threading
from time import sleep
from typing import Optional, Union, Any, Type

from .multichainmonitor import MultiChainMonitor
from bridgeconst.consts import Chain

from ..eth.ethtype.hexbytes import EthHashBytes
from ..eth.managers.exceptions import RpcEVMError
from ..logger import global_logger

from .utils import timestamp_msec
from .periodiceventabc import PeriodicEventABC
from .chaineventabc import ChainEventABC, TaskStatus, ReceiptParams
from ..prometheus_metric import PrometheusExporter


SendEventABC = Union[ChainEventABC, PeriodicEventABC]


class KeyValueCache:
    def __init__(self, value_type: Type, max_length: int):
        self.value_type = value_type
        self.max_length = max_length
        self.cache = dict()
        self.latest_item = None

    def _value_type_check(self, value: Any):
        if not isinstance(value, self.value_type):
            raise Exception("Not allowed type of value: expected({}), actual({})".format(self.value_type, type(value)))

    def add_value(self, key: int, value: Any):
        self._value_type_check(value)
        self.cache[key] = value
        self.latest_item = self._sort_dict()

        # remove old tokens if token list exceeds the maximum
        if len(self.cache.values()) > self.max_length:
            self._remove_half()

    def _sort_dict(self) -> Any:
        listed_items = list(self.cache.items())
        sorted_list = sorted(listed_items)
        self.cache = dict(sorted_list)
        return sorted_list[-1][1]

    def _remove_half(self):
        listed_items = list(self.cache.items())
        reduced_list = listed_items[len(listed_items):]
        self.cache = dict(reduced_list)

    def included_key(self, idx: int) -> bool:
        return idx in self.cache.keys()

    def included_value(self, value: int) -> bool:
        self._value_type_check(value)
        return value in self.cache.values()

    def get_value(self, key: int) -> Optional[Any]:
        return self.cache.get(key)


class EventBridge(MultiChainMonitor):
    def __init__(self, multichain_config: dict, cache_value_type: Type = int, max_length: int = 100):
        super().__init__(multichain_config)
        self.cache = KeyValueCache(cache_value_type, max_length)

    def has_key(self, key: int) -> bool:
        if self.cache is None:
            raise Exception("Authority checker is not initiated yet.")
        return self.cache.included_key(key)

    def set_value_by_key(self, key: int, relayer_idx: Any):
        if self.cache is None:
            raise Exception("Authority checker is not initiated yet.")
        self.cache.add_value(key, relayer_idx)

    def get_value_by_key(self, key: int) -> Optional[int]:
        return self.cache.get_value(key)

    def get_latest_value(self):
        return self.cache.latest_item

    def _handle_call_event(self, event: ChainEventABC):
        # build call transaction using the event
        chain_index, contract_name, method_name, params_tuple = event.build_call_transaction_params()

        # get result by call transaction
        result = self.world_call(chain_index, contract_name, method_name, params_tuple)

        # update event
        updated_event = event.handle_call_result(result)
        self.queue.enqueue(updated_event)

    def _handle_send_event(self, event: SendEventABC) -> Optional[SendEventABC]:
        # build transaction using the event
        dst_chain, contract_name, method_name, params = event.build_transaction_params()

        if isinstance(event, PeriodicEventABC):
            next_event = event.clone_next()
            self.queue.enqueue(next_event)

        if dst_chain == Chain.NONE or dst_chain is None:
            return None

        try:
            # build and send transaction
            tx = self.world_build_transaction(dst_chain, contract_name, method_name, params)
            tx_hash = self.world_send_transaction(dst_chain, tx, event.gas_limit_multiplier())

            global_logger.formatted_log(
                "Consumer",
                address=self.active_account.address,
                related_chain=dst_chain,
                msg="{}:txHash({}):nonce({})".format(event.summary(), tx_hash.hex(), tx.nonce)
            )

            if tx_hash == EthHashBytes.default():
                """ expected fee issue """
                global_logger.formatted_log(
                    "Consumer",
                    address=self.active_account.address,
                    related_chain=dst_chain,
                    msg="{}:ZeroTxHash".format(event.summary())
                )
                event.time_lock = timestamp_msec() + 3000
                self.queue.enqueue(event)
            else:
                """ set receipt params to the event """
                receipt_time_lock = timestamp_msec() + self.get_chain_manager_of(dst_chain).tx_commit_time_sec * 1000
                event.switch_to_check_receipt(dst_chain, tx_hash, receipt_time_lock)
                self.queue.enqueue(event)

        except RpcEVMError as e:
            # not-consume user nonce.
            global_logger.formatted_log(
                "Evm",
                address=self.active_account.address,
                related_chain=dst_chain,
                msg="{}:EvmError:{}".format(event.summary(), str(e))
            )
            # TODO does not update event when reverted poll filtered error occurs
            updated_event = event.handle_tx_result_fail()
            self.queue.enqueue(updated_event)

    def _handle_receipt_event(self, event: SendEventABC):
        receipt_params: ReceiptParams = event.get_receipt_params()
        receipt = self.world_receipt_with_wait(receipt_params.on_chain, receipt_params.tx_hash)

        if receipt is None:
            updating_func = event.handle_tx_result_fail
            log_status = "no-receipt"
        elif receipt.status == 1:
            updating_func = event.handle_tx_result_success
            log_status = "success"
        elif receipt.status == 0:
            updating_func = event.handle_tx_result_fail
            log_status = "fail"
        else:
            raise Exception("Not allowed receipt status")

        global_logger.formatted_log(
            "Receipt",
            address=self.active_account.address,
            related_chain=receipt_params.on_chain,
            msg="{}:receipt({}):{}".format(event.summary(), receipt_params.tx_hash.hex(), log_status)
        )

        # restart relayer after 60 secs
        if log_status == "no-receipt":
            global_logger.formatted_log(
                "Receipt",
                address=self.active_account.address,
                related_chain=receipt_params.on_chain,
                msg="{}:RestartAfter{}Second".format(event.summary(), 60)
            )
            sleep(60)
            os.execl(sys.executable, sys.executable, *sys.argv)

        updated_event = updating_func()
        self.queue.enqueue(updated_event)

    def run_world_task_manager(self):
        """
        A runner for transaction sender of relayer.
        """
        while True:
            event = self.queue.pop_matured_event()

            if event is None:
                continue

            if event.task_status == TaskStatus.CallTx:
                self._handle_call_event(event)

            elif event.task_status == TaskStatus.SendTX:
                self._handle_send_event(event)

            elif event.task_status == TaskStatus.CheckReceipt:
                self._handle_receipt_event(event)
            else:
                raise Exception("Invalid Task Status")

    def run_eventbridge(self):
        """
        An entry method to run relayer including runners: chain monitor and transaction sender
        """
        # bootstrap historical event; result is dummy return for process sync.
        _ = self.bootstrap_chain_events()

        # set oracle task to relay
        self._generate_periodic_offchain_task()

        # try:
        monitor_th = threading.Thread(target=self.run_world_chain_monitor)
        monitor_th.daemon = True
        sender_th = threading.Thread(target=self.run_world_task_manager)
        sender_th.daemon = True
        monitor_th.start()
        sender_th.start()

        while True:
            monitor_alive = monitor_th.is_alive()
            PrometheusExporter.exporting_thread_alive("monitor", monitor_alive)
            if not monitor_alive:
                global_logger.formatted_log(
                    "Bridge",
                    address=self.active_account.address,
                    msg="ThreadHealthCheck:Monitor thread has been dead. re-boot after 60 secs"
                )
                sleep(60)
                os.execl(sys.executable, sys.executable, *sys.argv)

            sender_alive = sender_th.is_alive()
            PrometheusExporter.exporting_thread_alive("sender", sender_alive)
            if not sender_alive:
                global_logger.formatted_log(
                    "Bridge",
                    address=self.active_account.address,
                    msg="ThreadHealthCheck:Sender thread has been dead. re-boot after 60 secs"
                )
                sleep(60)
                os.execl(sys.executable, sys.executable, *sys.argv)

            global_logger.formatted_log(
                "Bridge",
                address=self.active_account.address,
                msg="ThreadHealthCheck:Check the survival of the threads every 60 seconds."
            )

            sleep(120)
