from typing import Dict

from prometheus_client import Gauge, start_http_server

MONITOR_ALIVE_QUERY_NAME = "relayer_monitor_alive"
SENDER_ALIVE_QUERY_NAME = "relayer_sender_alive"
RPC_REQUESTS_QUERY_NAME = "relayer_rpc_requests_on_chain"
RPC_FAILURES_QUERY_NAME = "relayer_rpc_failures_on_chain"


class PrometheusExporter:
    PROMETHEUS_ON = False
    PROMETHEUS_SEVER_PORT = 8000

    MONITOR_THREAD_ALIVE = Gauge(MONITOR_ALIVE_QUERY_NAME, "Description")
    SENDER_THREAD_ALIVE = Gauge(SENDER_ALIVE_QUERY_NAME, "Description")
    RPC_CHAIN_INIT: Dict[str, bool] = dict()
    RPC_REQUESTED = Gauge(RPC_REQUESTS_QUERY_NAME, "Description", ["chain"])
    RPC_FAILED = Gauge(RPC_FAILURES_QUERY_NAME, "Description", ["chain"])

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
    def init_metrics(chain_name: str):
        chain_name = chain_name.lower()
        if PrometheusExporter.RPC_CHAIN_INIT.get(chain_name) is None:
            PrometheusExporter.RPC_REQUESTED.labels(chain_name).set(0)
            PrometheusExporter.RPC_FAILED.labels(chain_name).set(0)
            PrometheusExporter.RPC_CHAIN_INIT[chain_name] = True

    @staticmethod
    def exporting_rpc_requested(chain_name: str):
        if not PrometheusExporter.PROMETHEUS_ON:
            return
        PrometheusExporter.init_metrics(chain_name=chain_name)

        PrometheusExporter.RPC_REQUESTED.labels(chain_name).inc()

    @staticmethod
    def exporting_rpc_failed(chain_name: str):
        if not PrometheusExporter.PROMETHEUS_ON:
            return
        PrometheusExporter.init_metrics(chain_name=chain_name)

        PrometheusExporter.RPC_FAILED.labels(chain_name).inc()
