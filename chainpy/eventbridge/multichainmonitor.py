import time
from queue import PriorityQueue
from typing import Union, List, Tuple

from chainpy.eth.managers.eventobj import DetectedEvent
from chainpy.eth.managers.multichainmanager import MultiChainManager
from chainpy.eventbridge.chaineventabc import ChainEventABC
from chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger


class TimePriorityQueue:
    """
    Time-Priority Queue (Variant of Queue) that retrieves open items in time priority order (the soonest first).
     - time of item in the Queue, means "Time lock" which indicates when the item can be used.

    Methods
    @ enqueue(event); event must have "time_lock" member.
    @ pop_matured_item() -> Pop an item with a time lock earlier than the current time. (or block process)

    """
    STAY_PERIOD_SEC = 180  # 3 minutes

    def __init__(self, max_size: int = -1):
        self._queue = PriorityQueue(maxsize=max_size)

    def enqueue(self, event: Union[ChainEventABC, PeriodicEventABC]):
        # do nothing for a none event
        if event is None:
            return None

        # do nothing for event with invalid time lock
        if event.time_lock < 0:
            return None

        # check event types
        if not isinstance(event, ChainEventABC) and not isinstance(event, PeriodicEventABC):
            raise Exception(
                "Only allowed \"ChainEventABC\" or \"PeriodicEventABC\" types, but actual {}".format(type(event))
            )

        # enqueue item with time lock
        self._queue.put((event.time_lock, event))

    def pop(self) -> Union[ChainEventABC, PeriodicEventABC, None]:
        """ Pop the item with the soonest time lock, or block this process until the queue is not empty. """
        item = self._queue.get()[1]
        self._queue.task_done()
        return item

    def qsize(self) -> int:
        return self._queue.qsize()

    def pop_matured_event(self):
        """ Pop an item with a time lock earlier than the current time. (or block process) """
        item: Union[ChainEventABC, PeriodicEventABC] = self.pop()
        if timestamp_msec() >= item.time_lock:
            return item

        # re-enqueue if the item is not matured.
        self.enqueue(item)
        time.sleep(1)
        return None


class MultiChainMonitor(MultiChainManager):
    def __init__(self, multichain_config: dict):
        super().__init__(multichain_config)
        self._queue = TimePriorityQueue()
        self._events_types = dict()  # event_name to event_type
        self._offchain_source_types = dict()

    @property
    def queue(self) -> TimePriorityQueue:
        return self._queue

    @queue.setter
    def queue(self, queue: TimePriorityQueue):
        self._queue = queue

    def register_chain_event_obj(self, event_name: str, event_type: type):
        if not issubclass(event_type, ChainEventABC):
            raise Exception("event type to be registered must subclass of EventABC")
        if event_name in self._events_types.keys():
            raise Exception("Already existing type: {}".format(event_type))
        self._events_types[event_name] = event_type

    def register_offchain_event_obj(self, source_id: str, source_type: type):
        if not issubclass(source_type, PeriodicEventABC):
            raise Exception("oracle source type to be registered must subclass of EventABC")
        if source_id in self._offchain_source_types.keys():
            raise Exception("Already existing type: {}".format(source_type))
        self._offchain_source_types[source_id] = source_type

    def generate_periodic_offchain_task(self):
        for source_id, source_type in self._offchain_source_types.items():
            source_obj = source_type(self)
            self._queue.enqueue(source_obj)

    @staticmethod
    def extract_specific_events(
        event_name: str, detected_events: List[DetectedEvent]
    ) -> Tuple[List[DetectedEvent], List[DetectedEvent]]:
        targets, remainders = list(), list()
        for detected_event in detected_events:
            if detected_event.event_name == event_name:
                targets.append(detected_event)
            else:
                remainders.append(detected_event)
        return targets, remainders

    def bootstrap_chain_events(self):
        # collect events of every type on every chain
        detected_events = list()
        for chain_name in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_name)
            start_height = chain_manager.latest_height
            detected_events += chain_manager.collect_unchecked_single_chain_events(matured_only=True)
            global_logger.formatted_log(
                "BootStrap",
                address=chain_manager.account.address,
                related_chain_name=chain_name,
                msg="CollectEvents:from({}):to({})".format(start_height, chain_manager.latest_height)
            )

        for event_name, event_class in self._events_types.items():
            target_events, detected_events = self.extract_specific_events(event_name, detected_events)
            not_handled_events = event_class.bootstrap(self, target_events)
            for not_handled_event in not_handled_events:
                self._queue.enqueue(not_handled_event)
        return True

    def run_world_chain_monitor(self):
        """
        A runner to find the designated event from blockchains. Whenever detecting the event, enqueue it.
        """
        while True:
            detected_events = self.collect_unchecked_multichain_events()
            for detected_event in detected_events:
                event_type = self._events_types[detected_event.event_name]

                chain_event = event_type.init(detected_event, timestamp_msec(), self)
                self._queue.enqueue(chain_event)

                if chain_event is not None:
                    global_logger.formatted_log(
                        "Monitor",
                        address=self.active_account.address,
                        related_chain_name=chain_event.on_chain_name,
                        msg="{}:Detected".format(chain_event.summary())
                    )
            time.sleep(self.multichain_config["chain_monitor_period_sec"])
