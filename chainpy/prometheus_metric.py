from prometheus_client import Gauge

from chainpy.eth.ethtype.hexbytes import EthAddress

MONITOR_THREAD_ALIVE = Gauge("monitor_alive", "Description")
SENDER_THREAD_ALIVE = Gauge("monitor_alive", "Description")


def exporting_thread_alive(relayer_addr: EthAddress, thread_type: str, alive: bool):
    if relayer_addr == "0x9342CeaAc2d83a35e3d2fFEE4aADe9c3e87e00B7":
        if thread_type == "monitor":
            MONITOR_THREAD_ALIVE.set(int(alive))
        elif thread_type == "sender":
            SENDER_THREAD_ALIVE.set(int(alive))
        else:
            raise Exception("Not supported thread_type")
