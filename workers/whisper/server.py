"""
PyWorker works as a man-in-the-middle between the client and model API. It's function is:
1. receive request from client, update metrics such as workload of a request, number of pending requests, etc.
2a. transform the data and forward the transformed data to model API
2b. send updated metrics to autoscaler
3. transform response from model API(if needed) and forward the response to client

PyWorker forward requests to many model API endpoint. each endpoint must have an EndpointHandler. You can also
write function to just forward requests that don't generate anything with the model to model API without an
EndpointHandler. This is useful for endpoints such as healthchecks. See below for example
"""

import os
import logging
import dataclasses
from typing import Dict, Any, Type

from aiohttp import web, ClientResponse

from lib.backend import Backend, LogAction
from lib.data_types import EndpointHandler
from lib.server import start_server
from .data_types import InputData

# the url and port of model API
MODEL_SERVER_URL = "http://0.0.0.0:9000"


# This is the log line that is emitted once the server has started
MODEL_SERVER_START_LOG_MSG = "Application startup complete."
MODEL_SERVER_ERROR_LOG_MSGS = [
    "CUDA error",  # message in the logs indicating the unrecoverable error
    "CUDA out of memory",  # message in the logs indicating the unrecoverable error
]


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s[%(levelname)-5s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__file__)


# This class is the implementer for the '/asr' endpoint of model API
@dataclasses.dataclass
class AsrHandler(EndpointHandler[InputData]):

    benchmark_audio_duration_s: int = 30

    @property
    def endpoint(self) -> str:
        # the API endpoint
        return "/asr"

    @classmethod
    def payload_cls(cls) -> Type[InputData]:
        return InputData

    def generate_payload_json(self, payload: InputData) -> Dict[str, Any]:
        """
        defines how to convert `InputData` defined above, to
        json data to be sent to the model API
        """
        return dataclasses.asdict(payload)

    def make_benchmark_payload(self) -> InputData:
        """
        defines how to generate an InputData for benchmarking. This needs to be defined in only
        one EndpointHandler, the one passed to the backend as the benchmark handler
        """
        return InputData.for_test()

    async def generate_client_response(
        self, client_request: web.Request, model_response: ClientResponse
    ) -> web.Response:
        """
        defines how to convert a model API response to a response to PyWorker client
        """
        _ = client_request
        match model_response.status:
            case 200:
                log.debug("SUCCESS")
                data = await model_response.json()
                return web.json_response(data=data)
            case code:
                log.debug("SENDING RESPONSE: ERROR: unknown code")
                return web.Response(status=code)


class AsrBulkHandler(EndpointHandler[InputData]):
    @property
    def endpoint(self) -> str:
        return "/asr-bulk"

    @classmethod
    def payload_cls(cls) -> Type[InputData]:
        return InputData

    def generate_payload_json(self, payload: InputData) -> Dict[str, Any]:
        return dataclasses.asdict(payload)

    def make_benchmark_payload(self) -> InputData:
        return InputData.for_test()

    async def generate_client_response(
        self, client_request: web.Request, model_response: ClientResponse
    ) -> web.Response:
        """
        defines how to convert a model API response to a response to PyWorker client
        """
        _ = client_request
        match model_response.status:
            case 200:
                log.debug("SUCCESS")
                data = await model_response.json()
                return web.json_response(data=data)
            case code:
                log.debug("SENDING RESPONSE: ERROR: unknown code")
                return web.Response(status=code)


# This is the backend instance of pyworker. Only one must be made which uses EndpointHandlers to process
# incoming requests
backend = Backend(
    model_server_url=MODEL_SERVER_URL,
    model_log_file=os.environ["MODEL_LOG"],
    allow_parallel_requests=True,
    # give the backend a handler instance that is used for benchmarking
    # number of benchmark run and number of words for a random benchmark run are given
    benchmark_handler=AsrHandler(benchmark_runs=3, benchmark_audio_duration_s=10),
    # defines how to handle specific log messages. See docstring of LogAction for details
    log_actions=[
        (LogAction.ModelLoaded, MODEL_SERVER_START_LOG_MSG),
        (LogAction.Info, '100%'),
        *[
            (LogAction.ModelError, error_msg)
            for error_msg in MODEL_SERVER_ERROR_LOG_MSGS
        ],
    ],
)


# this is a simple ping handler for pyworker
async def handle_ping(_: web.Request):
    return web.Response(body="pong")


routes = [
    web.post("/asr", backend.create_handler(AsrHandler())),
    # web.post("/asr-bulk", backend.create_handler(AsrBulkHandler())),
    web.get("/ping", handle_ping),
]

if __name__ == "__main__":
    # start the PyWorker server
    start_server(backend, routes)
