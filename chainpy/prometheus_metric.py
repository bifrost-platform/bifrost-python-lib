from prometheus_client import Gauge, start_http_server

from chainpy.eth.ethtype.hexbytes import EthAddress

PROMETHEUS_ON = True
PROMETHEUS_SEVER_PORT = 8000


MONITOR_THREAD_ALIVE = Gauge("monitor_alive", "Description")
SENDER_THREAD_ALIVE = Gauge("sender_alive", "Description")
RPC_FAILED = Gauge("rpc_request_failures", "Description")
RPC_REQUESTED = Gauge("rpc_requested", "Description")


def init_prometheus_exporter():
    if not PROMETHEUS_ON:
        return
    start_http_server(PROMETHEUS_SEVER_PORT)


def exporting_thread_alive(thread_type: str, alive: bool):
    if not PROMETHEUS_ON:
        return
    if thread_type == "monitor":
        MONITOR_THREAD_ALIVE.set(int(alive))
    elif thread_type == "sender":
        SENDER_THREAD_ALIVE.set(int(alive))
    else:
        raise Exception("Not supported thread_type")


def exporting_rpc_requested():
    if not PROMETHEUS_ON:
        return
    RPC_REQUESTED.inc()


def exporting_rpc_failed():
    if not PROMETHEUS_ON:
        return
    RPC_FAILED.inc()
