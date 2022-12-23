from prometheus_client import Gauge, start_http_server


class PrometheusExporter:
    PROMETHEUS_ON = False
    PROMETHEUS_SEVER_PORT = 8000

    MONITOR_THREAD_ALIVE = Gauge("monitor_alive", "Description")
    SENDER_THREAD_ALIVE = Gauge("sender_alive", "Description")
    RPC_FAILED = Gauge("rpc_request_failures", "Description")
    RPC_REQUESTED = Gauge("rpc_requested", "Description")

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
    def exporting_rpc_requested():
        if not PrometheusExporter.PROMETHEUS_ON:
            return
        PrometheusExporter.RPC_REQUESTED.inc()

    @staticmethod
    def exporting_rpc_failed():
        if not PrometheusExporter.PROMETHEUS_ON:
            return
        PrometheusExporter.RPC_FAILED.inc()
