from typing import Dict

from prometheus_client import Gauge, start_http_server

from chainpy.eth.ethtype.consts import ChainIndex


MONITOR_ALIVE_QUERY_NAME = "relayer_monitor_alive"
SENDER_ALIVE_QUERY_NAME = "relayer_sender_alive"
RPC_REQUESTS_QUERY_NAME = "relayer_rpc_requests_on_{}"
RPC_FAILURES_QUERY_NAME = "relayer_rpc_failures_on_{}"


class PrometheusExporter:
    PROMETHEUS_ON = False
    PROMETHEUS_SEVER_PORT = 8000

    MONITOR_THREAD_ALIVE = Gauge(MONITOR_ALIVE_QUERY_NAME, "Description")
    SENDER_THREAD_ALIVE = Gauge(SENDER_ALIVE_QUERY_NAME, "Description")
    RPC_REQUESTED: Dict[ChainIndex, Gauge] = dict()
    RPC_FAILED: Dict[ChainIndex, Gauge] = dict()

    @staticmethod
    def init_prometheus_exporter(port: int = 8000):
        PrometheusExporter.PROMETHEUS_ON = True
        PrometheusExporter.PROMETHEUS_SEVER_PORT = port
        start_http_server(PrometheusExporter.PROMETHEUS_SEVER_PORT)

    @staticmethod
    def exporting_thread_alive(thread_type: str, alive: bool):
        if not PrometheusExporter.PROMETHEUS_ON:
            return
        if thread_type == "monitor":
            PrometheusExporter.MONITOR_THREAD_ALIVE.set(int(alive))
        elif thread_type == "sender":
            PrometheusExporter.SENDER_THREAD_ALIVE.set(int(alive))
        else:
            raise Exception("Not supported thread_type")

    @staticmethod
    def exporting_rpc_requested(chain_index: ChainIndex):
        if not PrometheusExporter.PROMETHEUS_ON:
            return

        chain_name = chain_index.name.lower()
        gauge = PrometheusExporter.RPC_REQUESTED.get(chain_index)
        if gauge is None:
            PrometheusExporter.RPC_REQUESTED[chain_index] = Gauge(
                RPC_REQUESTS_QUERY_NAME.format(chain_name),
                "Description"
            )
            PrometheusExporter.RPC_FAILED[chain_index] = Gauge(
                RPC_FAILURES_QUERY_NAME.format(chain_name),
                "Description"
            )
            PrometheusExporter.RPC_REQUESTED[chain_index].set(0)
            PrometheusExporter.RPC_FAILED[chain_index].set(0)

        PrometheusExporter.RPC_REQUESTED[chain_index].inc()

    @staticmethod
    def exporting_rpc_failed(chain_index: ChainIndex):
        if not PrometheusExporter.PROMETHEUS_ON:
            return

        gauge = PrometheusExporter.RPC_FAILED.get(chain_index)
        chain_name = chain_index.name.lower()
        if gauge is None:
            PrometheusExporter.RPC_REQUESTED[chain_index] = Gauge(
                RPC_REQUESTS_QUERY_NAME.format(chain_name),
                "Description"
            )
            PrometheusExporter.RPC_FAILED[chain_index] = Gauge(
                RPC_FAILURES_QUERY_NAME.format(chain_name),
                "Description"
            )
            PrometheusExporter.RPC_REQUESTED[chain_index].set(0)
            PrometheusExporter.RPC_FAILED[chain_index].set(0)

        PrometheusExporter.RPC_FAILED[chain_index].inc()
